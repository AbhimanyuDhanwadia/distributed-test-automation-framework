"""
Dependency Injection Container for the DTAF framework.
"""
from typing import Any, Dict, Type, Optional


class Container:
    """
    Simple Dependency Injection container for managing service dependencies.
    
    Supports both singleton and transient service lifetimes.
    """
    
    def __init__(self):
        """Initialize the container with empty service registrations."""
        self._services: Dict[Type, Dict[str, Any]] = {}
    
    def register(
        self,
        interface: Type,
        implementation: Any,
        singleton: bool = True
    ) -> None:
        """
        Register a service implementation for a given interface.
        
        Args:
            interface: The interface/abstract class to register
            implementation: The concrete implementation (class or instance)
            singleton: If True, creates a single instance; if False, creates new instances
        """
        self._services[interface] = {
            'implementation': implementation,
            'singleton': singleton,
            'instance': None
        }
    
    def resolve(self, interface: Type) -> Any:
        """
        Resolve and return an instance of the requested interface.
        
        Args:
            interface: The interface to resolve
            
        Returns:
            An instance of the registered implementation
            
        Raises:
            KeyError: If the interface is not registered
        """
        if interface not in self._services:
            raise KeyError(f"Service {interface} not registered in container")
        
        service_config = self._services[interface]
        implementation = service_config['implementation']
        
        if service_config['singleton']:
            # Return cached instance or create new one
            if service_config['instance'] is None:
                service_config['instance'] = (
                    implementation() if callable(implementation) else implementation
                )
            return service_config['instance']
        else:
            # Always create new instance for transient services
            return implementation() if callable(implementation) else implementation


# Global container instance
container = Container()
