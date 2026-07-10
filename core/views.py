from django.shortcuts import render


def landing(request):
    return render(request, "core/landing.html")


def blocked(request):
    return render(request, "core/blocked.html")
