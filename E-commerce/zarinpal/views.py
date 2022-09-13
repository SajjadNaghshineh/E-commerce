from django.shortcuts import render, redirect, get_object_or_404
from orders.models import Order
from django.http import HttpResponse
from zeep import Client
from .config import MERCHANT
from .tasks import payment_completed

client = Client('https://www.sandbox.zarinpal.com/pg/services/WebGate/wsdl')
amount = 1000
description = "تراکنش مربوط به خرید شما"
mobile = "09123456789"
CallbackURL = 'http://localhost:8000/zarinpal/verify/'

def send_request(request):
    order_id = request.session.get('order_id')
    order = get_object_or_404(Order, id=order_id)
    total_cost = order.get_total_cost()
    result = client.service.PaymentRequest(MERCHANT, total_cost, description, order.email, "mobile", CallbackURL)
    if result.Status == 100:
        return redirect('https://www.sandbox.zarinpal.com/pg/StartPay/' + str(result.Authority))
    else:
        return HttpResponse('Error code: ' + str(result.Status))
    
def verify(request):
    if request.GET.get('Status') == 'OK':
        order_id = request.session.get('order_id')
        order = get_object_or_404(Order, id=order_id)
        result = client.service.PaymentVerification(MERCHANT, request.GET['Authority'], amount)
        if result.Status == 100:
            order.paid = True
            order.save()
            payment_completed.delay(order.id)
            return render(request, "zarinpal/success.html", {"id": result.ReFID})
        elif request.Status == 101:
            return render(request, "zarinpal/submited.html", {"status": result.Status})
        else:
            return render(request, "zarinpal/failed.html", {"status": result.Status})
    else:
        return render(request, "zarinpal/cancel.html", {})
    