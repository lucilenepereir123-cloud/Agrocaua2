#!/usr/bin/env python
"""
Seed test data for AgroCaua IoT system
"""
from datetime import datetime, timedelta, timezone
from app import app, db
from models import DadosIoT

def seed_test_data():
    """Add test sensor data to the database"""
    with app.app_context():
        # Clear existing data
        DadosIoT.query.delete()
        db.session.commit()
        
        # Create test data for the last 24 hours
        base_time = datetime.now(timezone.utc)
        
        for i in range(24):
            # Generate data with variations
            timestamp = base_time - timedelta(hours=i)
            
            # Temperature varies throughout the day (15-30°C)
            temp = 20 + 10 * (0.5 + 0.5 * (1 - abs((i - 12) / 12)))
            
            # Humidity varies inversely with temperature
            humidity = 55 + 30 * (1 - (0.5 + 0.5 * (1 - abs((i - 12) / 12))))
            
            # Pressure relatively stable
            pressure = 1012 + (i % 3) - 1
            
            # Soil humidity
            soil_humidity = 60 + 15 * (0.5 + 0.5 * (1 - abs((i - 6) / 12)))
            
            # Vibration detection (random)
            vibration = i % 5 == 0
            
            # Pest detection (rare)
            pest_detection = i == 5
            
            record = DadosIoT(
                device_id='ESP32_AGROCAUA_01',
                timestamp=timestamp,
                latitude=-23.5505,
                longitude=-46.6333,
                temperatura_ar=round(temp, 2),
                humidade_ar=round(humidity, 2),
                pressao_ar=round(pressure, 2),
                humidade_solo=round(soil_humidity, 2),
                vibracao=vibration,
                detecao_praga=pest_detection,
                tipo_praga='Broca do milho' if pest_detection else None,
                confianca=0.95 if pest_detection else None
            )
            db.session.add(record)
        
        db.session.commit()
        count = DadosIoT.query.count()
        print(f"✓ Added {count} test records to database")

if __name__ == '__main__':
    seed_test_data()
