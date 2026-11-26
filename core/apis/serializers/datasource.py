import logging

from core.apis.datetime import DateTimeModelSerializer
from core.models import Datasource
from library.restframeworkflexfields import FlexFieldsModelSerializer

logger = logging.getLogger(__name__)


class DatasourceSerializer(FlexFieldsModelSerializer, DateTimeModelSerializer, ):
    class Meta:
        model = Datasource
        fields = [
            'base64pk',
            'datasource_id',
            'datasource_name',
            'engine',
            'database',
            'user',
            'password',
            'host',
            'port',
            'url',
            'created',
            'modified',
            'read_only',
            'enable',
            'properties',
            'description',
            'is_removed',
        ]
        extra_kwargs = {
            'base64pk': {'required': False, },
            'datasource_id': {'required': False, },
            'engine': {'required': False, },
            'database': {'required': False, },
            'user': {'required': False, },
            'password': {'required': False, },
            'host': {'required': False, },
            'port': {'required': False, },
            'url': {'required': False, },
            'is_removed': {'required': False, },
        }
        expandable_fields = {}
