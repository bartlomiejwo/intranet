from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from django.template import Template, RequestContext
from .models import Page


def dynamic_page_view(request, page_url):
    page_data = get_object_or_404(Page, url=page_url)
    template = Template(page_data.content)

    context = RequestContext(request, {'title': page_data.title})
    return HttpResponse(template.render(context))
