from html.parser import HTMLParser
import logging
import os
from urllib.parse import unquote

from django.conf import settings
from django.urls import reverse

from files_management.models import IntranetFile
from intranet_project import general_functions


logger = logging.getLogger(__name__)


class HTMLContentIntranetFilesFinder(HTMLParser):
    TAGS_TO_BE_SEARCHED = ['img', 'a', 'video', 'source',]
    ATTRS_TO_BE_SEARCHED = ['href', 'src', 'alt', 'poster',]

    def __init__(self):
        super().__init__()

        self.intranet_files = set()

    def handle_starttag(self, tag, attrs):
        self.parse_used_intranet_files(tag, attrs)

    def parse_used_intranet_files(self, tag, attrs):
        if tag in HTMLContentIntranetFilesFinder.TAGS_TO_BE_SEARCHED:
            for attr in attrs:
                if attr[0] in HTMLContentIntranetFilesFinder.ATTRS_TO_BE_SEARCHED:
                    local_path = HTMLContentIntranetFilesFinder.get_local_file_path(attr[1])

                    if local_path:
                        intranet_file = general_functions.get_object_or_none(IntranetFile, file=unquote(local_path))

                        if intranet_file is not None:
                            self.intranet_files.add(intranet_file)

    @staticmethod
    def get_local_file_path(url):
        if settings.MEDIA_NAME + '/' + settings.FILES_MANAGEMENT_DIR_NAME in url:
            file_path = url[url.index(settings.FILES_MANAGEMENT_DIR_NAME):]
            file_path_split = file_path.split('/')

            if file_path_split[0] == settings.FILES_MANAGEMENT_DIR_NAME \
                and len(file_path_split[1]) == 2 and len(file_path_split[2]) == 2:
                return file_path
        
        return None 
