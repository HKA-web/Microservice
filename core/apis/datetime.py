from django.db import models
from rest_framework import serializers


class DateTimeFieldSerializer(serializers.DateTimeField, ):

    def to_representation(self, value):
        if not value:
            return None
        datetimezone = self.enforce_timezone(value)
        datetime = datetimezone.replace(tzinfo=None, )
        offsite = datetimezone.strftime('%z')
        return dict(
            zone=f'{offsite[0:3]}:{offsite[3:]}',
            utc=value,
            date=datetime.strftime('%Y-%m-%d'),
            time=datetime.strftime('%H:%M:%S.%f'),
            datetime=datetime,
            datetimezone=datetimezone,
        )


class DateTimeModelSerializer(serializers.ModelSerializer, ):
    serializer_field_mapping = {
        **serializers.ModelSerializer.serializer_field_mapping,
        models.DateTimeField: DateTimeFieldSerializer,
    }
