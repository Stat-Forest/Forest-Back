# from rest_framework import serializers
# from apps.general.models import Organization
#
#
# class OrganizationMiniSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Organization
#         fields = ("id", "name")
#
#
# class RegionOrganizationsSerializer(serializers.Serializer):
#     region = serializers.CharField()
#     count = serializers.IntegerField()
#     display = serializers.CharField()
#     organizations = OrganizationMiniSerializer(many=True)
#
#
# class RepublicSerializer(serializers.Serializer):
#     label = serializers.CharField()
#     count = serializers.IntegerField()
#     display = serializers.CharField()
#
#
# class OrganizationsByRegionResponseSerializer(serializers.Serializer):
#     republic = RepublicSerializer()
#     regions = RegionOrganizationsSerializer(many=True)
