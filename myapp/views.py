
from django.shortcuts import render

def index(request):
    return render(request,'myapp/index.html')
def apply(request):
    return render(request,'myapp/apply.html')

# Create your views here.
