```mermaid
---
config:
  theme: mc
  look: classic
---
classDiagram
    class SpatialOperations {
        +name_lst: dict
        +read_fnc: function
        +parallel: bool
        +current_frame: GeoDataFrame
        +previous_frame: GeoDataFrame
        +threshold: float
        --
        +spatial_operations()
        +initialize_parameters()
        +load_feature_files()
        +setup_edges_and_geotransform()
        +operations()
        +process_frame_pair()
    }

    class OverlayAnalysis {
        --
        +overlay_()
        +calculate_intersections()
    }

    class SpatialClassification {
        --
        +continuous()
        +merge() 
        +split()
        +merge_split()
        +trajectory()
        +expansion()
        +count_inside()
        +edge_clusters()
    }

    class VectorMethods {
        --
        +split_mtd()
        +merge_mtd()
        +innercores_mtd()
        +opticalflow_mtd()
        +ellipse_mtd()
    }

    class Validation {
        --
        +validation()
        +quality_control()
    }

    SpatialOperations --> OverlayAnalysis : usa
    SpatialOperations --> SpatialClassification : usa
    SpatialOperations --> VectorMethods : aplica
    Validation --> VectorMethods : valida
    %% Validation --> SpatialOperations : retorna
```