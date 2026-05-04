from django.shortcuts import render

# Create your views here.
due_at = calculate_due_at(created_at, sla_hours, config)