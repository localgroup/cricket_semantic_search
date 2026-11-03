from rest_framework import serializers

class ChatRequestSerializer(serializers.Serializer):
    question = serializers.CharField(max_length=8000, allow_blank=False, trim_whitespace=True)
    top_k = serializers.IntegerField(required=False, default=5, min_value=1, max_value=10)

class IngestRequestSerializer(serializers.Serializer):
    file_path = serializers.CharField(required=False, max_length=1000)
