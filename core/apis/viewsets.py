import json
import logging
from collections import OrderedDict

from django.db import models
from django.db.models import Count
from django.http import QueryDict
from rest_framework import status
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from core.apis.filters import DevExtremeFilterBackend
from core.apis.mixins import DevExtremeMixin
from core.apis.mixins import DevExtremeSummaryMixin
from core.apis.paginations import DevExtremeTakeSkipPagination

logger = logging.getLogger(__name__)


def format_items(lvl_dict, lvl_items):
    if lvl_dict is None:
        return
    for key in lvl_dict:
        key_dict = lvl_dict[key]
        item = {'key': key}
        lvl_items.append(item)
        if 'count' in key_dict:
            item['count'] = key_dict['count']
        if 'summary' in key_dict:
            item['summary'] = key_dict['summary']
        if key_dict['items'] is None:
            item['items'] = None
        else:
            item['items'] = []
            format_items(key_dict['items'], item['items'])


class DevExtremeModelViewSet(ModelViewSet, DevExtremeMixin, DevExtremeSummaryMixin, ):
    pagination_class = DevExtremeTakeSkipPagination
    filter_backends = [DevExtremeFilterBackend, *ModelViewSet.filter_backends, ]

    def data(self, request):
        if isinstance(request.data, QueryDict):
            return request.data.dict()
        return request.data

    def create(self, request, *args, **kwargs):
        if not isinstance(request.data, list):
            if isinstance(request.data, QueryDict):
                data = request.data.dict()
                for key, value in kwargs.get('extras', {}).items():
                    data.update({key: json.dumps(value) if isinstance(value, dict) and not isinstance(self.get_queryset().model._meta.get_field(key), models.JSONField) else value, })
                result = QueryDict('', mutable=True, )
                result.update(data)
            else:
                result = request.data
                for key, value in kwargs.get('extras', {}).items():
                    result.update({key: json.dumps(value) if isinstance(value, dict) and not isinstance(self.get_queryset().model._meta.get_field(key), models.JSONField) else value, })
        else:
            result = request.data
            for index, data in enumerate(request.data):
                for key, value in kwargs.get('extras', [])[index].items() if len(kwargs.get('extras', [])) > index else dict().items():
                    result[index].update({key: json.dumps(value) if isinstance(value, dict) and not isinstance(self.get_queryset().model._meta.get_field(key), models.JSONField) else value, })
        serializer = self.get_serializer(data=result, many=isinstance(request.data, list), )
        serializer.is_valid(raise_exception=True, )
        self.perform_create(serializer, )
        headers = self.get_success_headers(serializer.data, )
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED,
            headers=headers,
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        if isinstance(request.data, QueryDict):
            data = request.data.dict()
            for key, value in kwargs.get('extras', {}).items():
                data.update({key: json.dumps(value) if isinstance(value, dict) and isinstance(getattr(instance, key), str) and not isinstance(self.get_queryset().model._meta.get_field(key), models.JSONField) else value, })
            result = QueryDict('', mutable=True, )
            result.update(data)
        else:
            result = request.data
            for key, value in kwargs.get('extras', {}).items():
                result.update({key: json.dumps(value) if isinstance(value, dict) and isinstance(getattr(instance, key), str) and not isinstance(self.get_queryset().model._meta.get_field(key), models.JSONField) else value, })
        serializer = self.get_serializer(instance, data=result, partial=partial, )
        serializer.is_valid(raise_exception=True, )
        self.perform_update(serializer, )
        setattr(instance, '_prefetched_objects_cache', getattr(instance, '_prefetched_objects_cache', {}))
        return Response(serializer.data, )

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        group = self.get_param_from_request(request, 'group')
        if group is None:
            return self._not_grouped_list(queryset, request)
        else:
            return self._grouped_list(group, queryset, request)

    def _grouped_list(self, groups, queryset, request):
        require_group_count = self.get_param_from_request(request, 'requireGroupCount')
        require_total_count = self.get_param_from_request(request, 'requireTotalCount')
        if not isinstance(groups, list):
            groups = [groups]
        group_field_names = {self.get_group_field_name(group) for group in groups}
        ordering = self.get_ordering(groups)
        group_queryset = queryset.values(*group_field_names).annotate(count=Count('pk')).order_by(*ordering).distinct()
        group_summary = self.get_param_from_request(request, 'groupSummary')
        if group_summary is not None and group_summary:
            group_summary_list = group_summary if isinstance(group_summary, list) else [group_summary]
            group_queryset = self.add_summary_annotate(group_queryset, group_summary_list)
        page = self.paginate_queryset(group_queryset)
        response_dict = {}
        if require_group_count:
            response_dict['groupCount'] = group_queryset.count()
        if require_total_count:
            response_dict['totalCount'] = queryset.count()
        rs = page if page is not None else group_queryset
        data_dict = {}
        for row in rs:
            level_dict = data_dict
            for group in groups:
                group_field_name = self.get_group_field_name(group)
                key = row[group_field_name]
                key = key[0] if isinstance(key, list) else key
                if key in level_dict:
                    key_dict = level_dict[key]
                else:
                    key_dict = {}
                    level_dict[key] = key_dict
                if 'isExpanded' in group and group['isExpanded']:
                    if 'items' not in key_dict:
                        key_dict['items'] = {}
                    level_dict = key_dict['items']
                else:
                    key_dict['items'] = None
                    key_dict['count'] = row['count']
                    summary_pairs = list(filter(lambda current: current[0].startswith('gs__'), row.items()))
                    if summary_pairs:
                        summary_pairs.sort(key=lambda current: current[0])
                        summary = [current[1] for current in summary_pairs]
                        key_dict['summary'] = summary
        response_dict['data'] = []
        format_items(data_dict, response_dict['data'])
        return Response(response_dict)

    def _not_grouped_list(self, queryset, request):
        response_dict = OrderedDict()
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            response_dict['totalCount'] = self.paginator.count
        else:
            serializer = self.get_serializer(queryset, many=True)
        total_summary = self.get_param_from_request(request, 'totalSummary')
        if total_summary is not None and total_summary:
            total_summary_list = total_summary if isinstance(total_summary, list) else [total_summary]
            response_dict['summary'] = self.calc_total_summary(queryset, total_summary_list)
        response_dict['data'] = serializer.data
        return Response(response_dict)

    def get_group_field_name(self, group):
        if 'groupInterval' in group:
            return group['selector'].replace('.', '__') + '__' + group['groupInterval']
        else:
            return group['selector'].replace('.', '__')


