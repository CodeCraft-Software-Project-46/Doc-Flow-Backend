from django.db import transaction
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .models import WorkingHoursConfig
from .serializers import WorkingHoursSerializer

# GET CONFIG
@api_view(['GET']) #This function ONLY accepts GET requests"
def get_config(request):
    # Explicit ordering: with only one config row this doesn't change the
    # result, but it removes the ambiguity if a second row is ever created.
    config = WorkingHoursConfig.objects.order_by('id').first()

    if not config: #If DB is empty:
        return Response(                                 #{
            {"exists": False, "data": None},             #"exists": False,
            status=status.HTTP_200_OK                    #"data": None,
        )                                                #}

    serializer = WorkingHoursSerializer(config)  #converts Python object → JSON
    return Response(
        {"exists": True, "data": serializer.data},
        status=status.HTTP_200_OK
    )

# SAVE / UPDATE CONFIG
@api_view(['POST'])
def save_config(request):
    # select_for_update + atomic: two concurrent first-time saves used to be
    # able to both see "no config yet" and each create their own row. Locking
    # here makes the read-then-create/update a single atomic step.
    with transaction.atomic():
        config = (
            WorkingHoursConfig.objects
            .select_for_update()
            .order_by('id')
            .first()
        )

        if config:
            serializer = WorkingHoursSerializer(config, data=request.data, partial=True)  #partial=True → you can send only some fields
        else:
            serializer = WorkingHoursSerializer(data=request.data)   #Create new row

        if serializer.is_valid():#validate data requred fields, correct data types, etc.that defined in model
            serializer.save() #save to database
            return Response(
                {
                    "message": "Working hours configuration saved successfully",
                    "data": serializer.data
                },
                status=status.HTTP_200_OK
            )
        return Response(
            {
                "message": "Validation failed",
                "errors": serializer.errors
            },
            status=status.HTTP_400_BAD_REQUEST
        )