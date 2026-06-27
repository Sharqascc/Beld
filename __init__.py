"""
Beld — modular floor-plan generation framework.

Quick start
-----------
from beld.pipeline import FloorPlanPipeline
from beld.models import Room
from shapely.geometry import Polygon

rooms = [
    Room("R1", Polygon([(0,0),(5,0),(5,4),(0,4)]), "living", 20.0),
    Room("R2", Polygon([(5,0),(10,0),(10,4),(5,4)]), "kitchen", 20.0),
]
plan = FloorPlanPipeline().run(rooms)
"""

__version__ = "0.1.0"
