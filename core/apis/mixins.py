import json
import logging

from django.db.models import *
from rest_framework.exceptions import ValidationError

logger = logging.getLogger(__name__)


class DevExtremeMixin(object, ):
    @classmethod
    def get_param_from_request(cls, request, param_name):
        def json_loads(value, default):
            try:
                json_object = json.loads(value)
            except json.JSONDecodeError as e:
                return default
            return json_object

        param_list = []
        if param_name in request.query_params:
            param_list = request.query_params.getlist(param_name)
        elif param_name + '[]' in request.query_params:
            param_list = request.query_params.getlist(param_name + '[]')

        param_list = [json_loads(param, param) for param in param_list]
        if len(param_list) == 1:
            return param_list[0]
        elif len(param_list) > 1:
            return param_list

        return request.data.get(param_name)

    @classmethod
    def get_ordering(cls, sort_list):
        result = []
        if sort_list is None:
            return result
        if isinstance(sort_list, dict):
            sort_list = [sort_list]
        for param in sort_list:
            result.append(('-' if 'desc' in param and param['desc'] else '') + param['selector'].replace('.', '__'))
        return result


def _get_aggregate_function(function_name, field_name):
    if function_name == 'count':
        return Count(field_name)
    elif function_name == 'avg':
        return Avg(field_name)
    elif function_name == 'max':
        return Max(field_name)
    elif function_name == 'min':
        return Min(field_name)
    elif function_name == 'sum':
        return Sum(field_name)
    else:
        raise ValidationError(detail='''Unsupported summary type '%s' ''' % function_name)


class DevExtremeSummaryMixin(object, ):

    def get_aggregate_function(self, function_name, field_name):
        return _get_aggregate_function(function_name, field_name)

    def calc_total_summary(self, queryset, summary_list):
        result = []
        for summary in summary_list:
            field_name = summary['selector'].replace('.', '__')
            aggr_function = self.get_aggregate_function(summary['summaryType'], field_name)
            if aggr_function is None:
                result.append(None)
            else:
                summary_qset = queryset.aggregate(aggr_function)
                result.append(list(summary_qset.values())[0])
        return result

    def add_summary_annotate(self, queryset, summary_list):
        summary_param_dict = {}
        for summary in summary_list:
            field_name = summary['selector'].replace('.', '__')
            aggr_function = self.get_aggregate_function(summary['summaryType'], field_name)
            param_name = 'gs__' + str(summary_list.index(summary))
            summary_param_dict[param_name] = aggr_function
        return queryset.annotate(**summary_param_dict)
