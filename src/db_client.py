#!/usr/bin/env python3
"""
Deutsche Bahn Client
Verwendet die Community API v6.db.transport.rest für Fahrplanabfragen
Produktionsversion - optimiert für Hamburg → Landeck-Zams Überwachung
"""

import requests
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class Station:
    """Repräsentiert eine Bahnstation"""
    id: str
    name: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None

@dataclass  
class Journey:
    """Repräsentiert eine Zugverbindung"""
    departure_time: datetime
    arrival_time: datetime
    duration_minutes: int
    transfers: int
    legs: List[Dict[str, Any]]
    raw_data: Dict[str, Any]

class DBClient:
    """Client für Deutsche Bahn Community API"""
    
    def __init__(self, timeout: int = 30):
        self.base_url = "https://v6.db.transport.rest"
        self.timeout = timeout
        self.logger = logging.getLogger(__name__)
        
        # Rate Limiting (100 requests/minute - Produktion: 25% Sicherheitsmarge)
        self.rate_limit_requests = 75  # 25% unter Maximum
        self.rate_limit_window = 60
        self.request_times = []
    
    def _check_rate_limit(self) -> bool:
        """Prüfe Rate Limit vor Request"""
        now = datetime.now()
        # Entferne alte Requests (älter als 1 Minute)
        self.request_times = [t for t in self.request_times if (now - t).seconds < self.rate_limit_window]
        
        if len(self.request_times) >= self.rate_limit_requests:
            self.logger.warning("Rate Limit erreicht - warte...")
            return False
        
        self.request_times.append(now)
        return True
    
    def _make_request(self, endpoint: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Führe API Request durch mit Rate Limiting"""
        if not self._check_rate_limit():
            return None
        
        url = f"{self.base_url}{endpoint}"
        try:
            self.logger.debug(f"API Request: {url} mit params: {params}")
            response = requests.get(url, params=params, timeout=self.timeout)
            
            if response.status_code == 200:
                return response.json()
            else:
                self.logger.error(f"API Error {response.status_code}: {response.text}")
                return None
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Request Exception: {str(e)}")
            return None
    
    def find_station(self, station_name: str) -> Optional[Station]:
        """Finde Station anhand des Namens"""
        params = {"query": station_name, "results": 5}
        data = self._make_request("/locations", params)
        
        if not data or not isinstance(data, list):
            return None
        
        # Suche nach exakter Übereinstimmung oder bester Match
        for location in data:
            if location.get("type") == "station":
                name = location.get("name", "")
                if station_name.lower() in name.lower() or name.lower() in station_name.lower():
                    station_id = location.get("id")
                    lat = location.get("location", {}).get("latitude")
                    lon = location.get("location", {}).get("longitude")
                    
                    return Station(
                        id=station_id,
                        name=name,
                        latitude=lat,
                        longitude=lon
                    )
        
        return None
    
    def search_journeys(self, 
                       from_station_id: str, 
                       to_station_id: str, 
                       departure_date: datetime,
                       max_results: int = 10) -> List[Journey]:
        """Suche Zugverbindungen zwischen zwei Stationen"""
        
        # Format: 2025-03-15T10:00:00+01:00
        departure_str = departure_date.isoformat()
        
        params = {
            "from": from_station_id,
            "to": to_station_id,
            "departure": departure_str,
            "results": max_results
        }
        
        data = self._make_request("/journeys", params)
        
        if not data or "journeys" not in data:
            self.logger.warning("Keine Verbindungen gefunden")
            return []
        
        journeys = []
        for journey_data in data["journeys"]:
            try:
                journey = self._parse_journey(journey_data)
                if journey:
                    journeys.append(journey)
            except Exception as e:
                self.logger.error(f"Fehler beim Parsen der Verbindung: {str(e)}")
                continue
        
        return journeys
    
    def _parse_journey(self, journey_data: Dict[str, Any]) -> Optional[Journey]:
        """Parse Journey Daten aus API Response"""
        try:
            legs = journey_data.get("legs", [])
            if not legs:
                return None
            
            # Departure Zeit vom ersten Leg
            first_leg = legs[0]
            departure_str = first_leg.get("departure")
            if not departure_str:
                return None
            
            # Arrival Zeit vom letzten Leg  
            last_leg = legs[-1]
            arrival_str = last_leg.get("arrival")
            if not arrival_str:
                return None
            
            # Parse Zeiten
            departure_time = datetime.fromisoformat(departure_str.replace('Z', '+00:00'))
            arrival_time = datetime.fromisoformat(arrival_str.replace('Z', '+00:00'))
            
            # Berechne Dauer
            duration = arrival_time - departure_time
            duration_minutes = int(duration.total_seconds() / 60)
            
            # Anzahl Umstiege
            transfers = len(legs) - 1
            
            return Journey(
                departure_time=departure_time,
                arrival_time=arrival_time,
                duration_minutes=duration_minutes,
                transfers=transfers,
                legs=legs,
                raw_data=journey_data
            )
            
        except Exception as e:
            self.logger.error(f"Fehler beim Parsen der Journey: {str(e)}")
            return None
    
    def get_month_connections(self, 
                            from_station_id: str, 
                            to_station_id: str, 
                            year: int,
                            month: int,
                            start_hour: int = 8) -> Dict[str, List[Journey]]:
        """Hole alle verfügbaren Verbindungen für einen bestimmten Monat"""
        connections_by_date = {}
        
        # Bestimme maximale Tageszahl für den Monat
        import calendar
        max_days = calendar.monthrange(year, month)[1]
        
        for day in range(1, max_days + 1):
            try:
                current_date = datetime(year, month, day, start_hour, 0)
                date_key = current_date.strftime("%Y-%m-%d")
                
                self.logger.info(f"Suche Verbindungen für {date_key}")
                
                journeys = self.search_journeys(from_station_id, to_station_id, current_date)
                if journeys:
                    connections_by_date[date_key] = journeys
                    self.logger.info(f"Gefunden: {len(journeys)} Verbindungen für {date_key}")
                else:
                    self.logger.debug(f"Keine Verbindungen für {date_key}")
            
            except ValueError as e:
                # Ungültiges Datum
                self.logger.debug(f"Tag {day} für {year}-{month:02d} ungültig: {str(e)}")
                continue
            except Exception as e:
                self.logger.error(f"Fehler bei Abfrage für {date_key}: {str(e)}")
                continue
        
        return connections_by_date
    
    def format_journey_summary(self, journey: Journey) -> str:
        """Formatiere Journey für Ausgabe"""
        dep_time = journey.departure_time.strftime("%H:%M")
        arr_time = journey.arrival_time.strftime("%H:%M")
        duration_hours = journey.duration_minutes // 60
        duration_mins = journey.duration_minutes % 60
        
        duration_str = f"{duration_hours}h {duration_mins}m"
        transfers_str = f"{journey.transfers} Umstieg{'e' if journey.transfers != 1 else ''}"
        
        return f"{dep_time} → {arr_time} ({duration_str}, {transfers_str})"


# Vordefinierte Station IDs (aus API-Exploration)
HAMBURG_HBF_ID = "8002549"
LANDECK_ZAMS_ID = "8100063"