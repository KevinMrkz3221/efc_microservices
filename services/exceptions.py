"""
Excepciones personalizadas para el servicio de Items
"""

class ItemServiceException(Exception):
    """Excepción base para errores del servicio de items"""
    pass

class ItemNotFoundError(ItemServiceException):
    """Error cuando no se encuentra un item"""
    pass

class ExternalAPIError(ItemServiceException):
    """Error al comunicarse con la API externa"""
    pass

class ValidationError(ItemServiceException):
    """Error de validación de datos"""
    pass
