# segment_config.py
SEGMENTS = {
    'iot': {
        'ip_range': '192.168.1.100-199',  # Virtual range for tracking
        'rules': {
            'block_internal': True,      # Can't access other devices
            'allow_internet': True,      # Can reach external services
            'allow_ports': [80, 443, 8883],  # Only specific ports
        }
    },
    'trusted': {
        'ip_range': '192.168.1.10-99',
        'rules': {
            'block_internal': False,     # Full internal access
            'allow_internet': True,
            'allow_ports': [],           # All ports
        }
    },
    'quarantine': {
        'ip_range': '192.168.1.200-254',
        'rules': {
            'block_internal': True,
            'allow_internet': False,     # Completely isolated
            'allow_ports': [],
        }
    }
}