from django import template
from custom_pages.models import Page, Tab


register = template.Library()

NAV_OBJECT_TYPES = {
    'PAGE': 'page',
    'TAB': 'tab',
}


@register.simple_tag
def NAV_OBJECT_TYPES_LIST():
    return NAV_OBJECT_TYPES


@register.simple_tag
def nav_objects_list():
    nav_objects_list = []
    get_tabs_data(nav_objects_list)
    get_pages_data(nav_objects_list)

    return sort_nav_objects_list(nav_objects_list)


def get_tabs_data(nav_objects_list):
    tabs = Tab.objects.all()

    for tab in tabs:
        tab_data = {'position': tab.position, 'type': NAV_OBJECT_TYPES['TAB'], 'area_name': tab.area_name, 'title': tab.title, 'subpages': []}
        nav_objects_list.append(tab_data)


def get_pages_data(nav_objects_list):
    pages = Page.objects.all()

    for page in pages:
        page_data = {'position': page.position, 'type': NAV_OBJECT_TYPES['PAGE'], 'url': page.url, 'title': page.title}

        if page.parent_tab:
            for item in nav_objects_list:
                if page.parent_tab.title == item['title']:
                    item['subpages'].append(page_data)
        else:
            nav_objects_list.append(page_data)


def sort_nav_objects_list(nav_objects_list):
    nav_objects_list = sorted(nav_objects_list, key=lambda k: k['position'])

    for item in nav_objects_list:
        if item['type'] == NAV_OBJECT_TYPES['TAB']:
            item['subpages'] = sorted(item['subpages'], key=lambda k: k['position'])

    return nav_objects_list
