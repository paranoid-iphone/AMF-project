from rest_framework import serializers


class HealthSerializer(serializers.Serializer[dict[str, str]]):
    status = serializers.CharField(read_only=True)
    database = serializers.CharField(read_only=True)


class UnavailableHealthSerializer(serializers.Serializer[dict[str, str]]):
    status = serializers.CharField(read_only=True)
    database = serializers.CharField(read_only=True)
