"""
drf-spectacular OpenAPI authentication extension for CustomJWTAuthentication.

This extension tells drf-spectacular how to document the custom JWT authentication
class in the OpenAPI schema, enabling the Authorize button in Swagger UI.
"""

from drf_spectacular.extensions import OpenApiAuthenticationExtension
from drf_spectacular.openapi import AutoSchema


class CustomJWTAuthenticationExtension(OpenApiAuthenticationExtension):
    """
    OpenAPI extension for CustomJWTAuthentication.
    
    Maps the custom JWT authentication class to the BearerAuth security scheme
    in the generated OpenAPI schema, which enables the Authorize button in Swagger UI.
    """
    
    target_class = 'apps.authentications.service.authentication.CustomJWTAuthentication'
    name = 'BearerAuth'
    
    def get_security_definition(self, auto_schema: AutoSchema):
        """
        Return the security scheme definition for Bearer JWT authentication.
        
        This definition will appear in the OpenAPI schema's components.securitySchemes
        section and will be used by Swagger UI to display the Authorize button.
        
        Returns:
            dict: Security scheme definition following OpenAPI 3.0 specification.
        """
        return {
            'type': 'http',
            'scheme': 'bearer',
            'bearerFormat': 'JWT',
        }
