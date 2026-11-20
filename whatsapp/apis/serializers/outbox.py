import logging
from core.apis.datetime import DateTimeModelSerializer
from library.restframeworkflexfields import FlexFieldsModelSerializer

from whatsapp.models import Outbox

logger = logging.getLogger(__name__)

class OutboxSerializer(FlexFieldsModelSerializer, DateTimeModelSerializer, ):
    class Meta:
        model = Outbox
        fields = [
            'base64pk',
            'outbox_id',
            'message',
            'message_type',
            'outbox_for',
            'prepare_date',
            'retry',
            'scheduled',
            'scheduled_date',
            'is_interactive',
            'is_answered',
            'answered_date',
            'data',
            'session_id',
            'created',
            'modified',
            'read_only',
            'enable',
            'properties',
            'description',
        ]
        extra_kwargs = {
            'base64pk': {'required': False, },
            'outbox_id': {'required': False, },
            'prepare_date': {'required': False, },
            'retry': {'required': False, },
            'scheduled': {'required': False, },
            'scheduled_date': {'required': False, },
            'is_interactive': {'required': False, },
            'is_answered': {'required': False, },
            'answered_date': {'required': False, },
            'data': {'required': False, },
            'created': {'required': False, },
            'modified': {'required': False, },
            'read_only': {'required': False, },
            'enable': {'required': False, },
            'properties': {'required': False, },
            'description': {'required': False, },
        }
        expandable_fields = {
            'session': (
                'whatsapp.apis.serializers.SessionSerializer', {'many': False, },
            )
        }

    def create(self, validated_data):
        using_db = validated_data.pop('using', 'WHATSAPP')
        return Outbox.objects.using(using_db).create(**validated_data)

    def update(self, instance, validated_data):
        using_db = validated_data.pop('using', 'WHATSAPP')
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save(using=using_db)
        return instance

