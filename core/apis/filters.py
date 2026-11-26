import logging

from django.db.models import Q
from rest_framework import filters

from core.apis.mixins import DevExtremeMixin

logger = logging.getLogger(__name__)


class DevExtremeFilterBackend(filters.BaseFilterBackend, DevExtremeMixin, ):

    def __init__(self):
        self.is_case_sensitive = self.get_case_sensitive()

    def __is_leaf(self, filter):
        for element in filter:
            if isinstance(element, list):
                return False
        return True

    def __to_django_operator(self, operator):
        if operator == '=':
            return ''
        elif operator == '>':
            return '__gt'
        elif operator == '<':
            return '__lt'
        elif operator == '>=':
            return '__gte'
        elif operator == '<=':
            return '__lte'
        else:
            return '__' + operator if self.is_case_sensitive else '__i' + operator

    def __leaf_node_to_q(self, leaf):
        field_name = (leaf[0].replace('.', '__')
                      .replace('__Year', '__year')
                      .replace('__Month', '__month')
                      .replace('__Day', '__day')
                      .replace('__Hour', '__hour')
                      .replace('__Minute', '__minute')
                      .replace('__Second', '__second'))
        if len(leaf) == 2 and leaf[1] not in ('=', '>', '<', '>=', '<=',):
            temporary = leaf[1]
            leaf[1] = '='
            leaf.append(temporary)
        if len(leaf) == 2 and leaf[1] == '=':
            kwargs = {field_name + '__isnull': True, }
            return Q(**kwargs)
        elif leaf[1] == '=' and not self.is_case_sensitive and isinstance(leaf[2], str):
            kwargs = {}
            if '__' not in field_name:
                kwargs[field_name + '__exact'] = leaf[2]
            else:
                kwargs[field_name + '__iexact'] = leaf[2]
            return Q(**kwargs)
        elif leaf[1] == '<>':
            kwargs = {}
            if not self.is_case_sensitive and isinstance(leaf[2], str):
                if '__' not in field_name:
                    kwargs[field_name + '__exact'] = leaf[2]
                else:
                    kwargs[field_name + '__iexact'] = leaf[2]
            else:
                kwargs[field_name] = leaf[2]
            return ~Q(**kwargs)
        elif leaf[1] == 'notcontains':
            kwargs = {}
            if self.is_case_sensitive:
                kwargs[field_name + '__contains'] = leaf[2]
            else:
                kwargs[field_name + '__icontains'] = leaf[2]
            return ~Q(**kwargs)
        elif isinstance(leaf[2], float):
            kwargs = {field_name + self.__to_django_operator(leaf[1]): str(leaf[2]), }
            return Q(**kwargs)
        else:
            kwargs = {field_name + self.__to_django_operator(leaf[1]): leaf[2], }
            return Q(**kwargs)

    def __generate_q_expr(self, filter):
        if filter is None or not filter:
            return None
        if self.__is_leaf(filter):
            return self.__leaf_node_to_q(filter)
        else:
            elements = []
            for element in filter:
                if isinstance(element, list):
                    elements.append(self.__generate_q_expr(element))
                elif element in ['and', 'or', '!']:
                    elements.append(element)
                else:
                    raise Exception('Could not implement this search')
            if elements[0] == '!':
                expression = ~elements[1]
            else:
                expression = elements[0]
                for num_pair in range(0, len(elements) // 2):
                    operator = elements[num_pair * 2 + 1]
                    if operator == 'and':
                        expression = expression & elements[(num_pair + 1) * 2]
                    elif isinstance(operator, Q):
                        expression = expression & operator
                    else:
                        expression = expression | elements[(num_pair + 1) * 2]
            return expression

    def filter_queryset(self, request, queryset, view):
        requeryset = queryset
        filter = self.get_param_from_request(request, 'filter')
        if filter:
            expression = self.__generate_q_expr(filter)
            if expression is not None:
                requeryset = requeryset.filter(expression)
        sort = self.get_param_from_request(request, 'sort')
        if sort:
            ordering = self.get_ordering(sort)
            if ordering:
                requeryset = requeryset.order_by(*ordering)
        return requeryset

    def get_case_sensitive(self):
        from django.conf import settings
        try:
            return settings.REST_FRAMEWORK['DEVEXTREME_DATAGRID']['FILTER_CASE_SENSITIVE']
        except (AttributeError, KeyError):
            return False
