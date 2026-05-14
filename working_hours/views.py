from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from .models import WorkingHoursConfig
from .serializers import WorkingHoursSerializer

# ======================================================
# GET CONFIG
# ======================================================
@api_view(['GET']) #This function ONLY accepts GET requests"
def get_config(request):
    config = WorkingHoursConfig.objects.first() #fetch data from DB It takes ONE full row (first record)  Only ONE config for whole company

    if not config: #If DB is empty: 
        return Response(                                 #{                   
            {"exists": False, "data": None},             #"exists": False, 
            status=status.HTTP_200_OK                    #"data": None,
        )                                                #}

    serializer = WorkingHoursSerializer(config)  #converts Python object → JSON
    return Response(
        {"exists": True, "data": serializer.data},
        status=status.HTTP_200_OK
    ) #send to frontend
     
#     {
#   "exists": true,
#   "data": {
#     "workStartTime": "09:00",
#     "workEndTime": "17:00",
#     "workDays": [1,2,3,4,5],
#     "holidays": []
#   }
# }

    #print(serializer)
    #print("*")
    #print(serializer.data)
    #print("*")

# ======================================================
# SAVE / UPDATE CONFIG
# ======================================================
@api_view(['POST'])
def save_config(request):
    #print(request)
    #print(request.data) #data from frontend
    config = WorkingHoursConfig.objects.first() #check if DB already has a record

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