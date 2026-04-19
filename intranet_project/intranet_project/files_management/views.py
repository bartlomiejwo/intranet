import os

from django.views.generic import ListView, View, CreateView
from django.shortcuts import render, get_object_or_404, redirect
from django.conf import settings
from django.http import Http404, FileResponse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from .models import IntranetFile
from .forms import IntranetFileCreateForm
from files_management import validation_codes


class UploadFileAjaxView(LoginRequiredMixin, View):
    def post(self, request):
        context = {
            'ok': True,
            'file_already_posted': False,
        }

        files = request.FILES
        uploaded_file = files.get('file', None)

        if uploaded_file:
            intranet_file = IntranetFile(
                file=uploaded_file,
                owner=request.user,
                name=uploaded_file.name,
                upload_date=timezone.now(),
                added_with_wysiwyg=False if request.POST.get('fromEditor', None) == 'false' else True,
            )

            try:
                intranet_file.clean()
            except ValidationError as e:
                if e.code == validation_codes.FILE_ALREADY_POSTED_BEFORE:
                    context['filename'] = uploaded_file.name
                    context['file_url'] = e.link
                    context['file_already_posted'] = True
                else:
                    context['ok'] = False
                    context['message'] = ' '.join(e.messages)
            else:
                intranet_file.save()

                context['filename'] = intranet_file.name
                context['file_url'] = intranet_file.get_link()
        else:
            context['ok'] = False
            content['message'] = _('An error occurred while uploading file.')

        return JsonResponse(context, status=200)


class UserIntranetFilesListView(LoginRequiredMixin, ListView):
    model = IntranetFile
    template_name = 'files_management/user_intranet_files.html'
    context_object_name = 'files'
    paginate_by = 20

    def get_queryset(self):
        return IntranetFile.objects.filter(owner=self.request.user).order_by(
            '-upload_date',
            '-added_with_wysiwyg'
        )


class IntranetFileCreateView(LoginRequiredMixin, CreateView):
    model = IntranetFile
    template_name = 'files_management/intranet_file_create.html'
    form_class = IntranetFileCreateForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['owner'] = self.request.user

        return kwargs

    def form_valid(self, form):
        form.instance.owner = self.request.user
        form.instance.upload_date = timezone.now()
        form.instance.file_content_hash = form.file_content_hash
        
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('files_management:user_files')


@login_required
def delete_intranet_files(request):
    if request.GET.get('id', None):
        intranet_files_ids = request.GET.getlist('id')
        intranet_files_to_delete = IntranetFile.objects.filter(id__in=intranet_files_ids, owner=request.user)

        files_to_delete_number = len(intranet_files_ids)
        files_deleted_number = len(intranet_files_to_delete)

        intranet_files_to_delete.delete()

        if files_deleted_number <= 0:
            messages.error(request, _('No files have been deleted.'))
        elif files_to_delete_number == files_deleted_number:
            if files_deleted_number == 1:
                messages.success(request, _('File was deleted successfully.'))
            else:
                messages.success(request, _('Files were deleted successfully.'))
        elif files_deleted_number < files_to_delete_number:
            messages.warning(request, _('%(files_deleted_number)s files were deleted.') \
                            % {'files_deleted_number': files_deleted_number})
        else:
            messages.error(request, _('An error occurred.'))

    return redirect('files_management:user_files')
