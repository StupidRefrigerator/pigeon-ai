import geopandas as gpd

from .paths import CRS


def select_population_context(boundaries, context_area):
    boundaries = boundaries.to_crs(CRS)
    intersects_context = boundaries.geometry.intersects(context_area)
    context = boundaries[intersects_context].copy()
    population = context["population"]
    assert population.notna().all(), "Missing population in contextual SA1s"
    assert (population >= 0).all(), "Negative SA1 population"

    # Select original polygons without clipping: denominators stay complete.
    context["sa1_area_m2"] = context.geometry.area
    assert (context["sa1_area_m2"] > 0).all(), "SA1 with no usable area"
    return context


def allocate_population(zones, context):
    intersections = gpd.overlay(
        zones[["hex_id", "geometry"]],
        context[["population", "sa1_area_m2", "geometry"]],
        how="intersection",
        keep_geom_type=True,
    )
    contribution = intersections["population"] * intersections.geometry.area
    intersections["contribution"] = contribution / intersections["sa1_area_m2"]
    return intersections.groupby("hex_id")["contribution"].sum(min_count=1)


def add_population_features(grid, boundaries):
    grid = grid.copy()
    grid_area = grid.geometry.union_all()
    context = select_population_context(boundaries, grid_area)
    population = allocate_population(grid, context)
    grid["population_est"] = grid["hex_id"].map(population).fillna(0)
    hex_area_km2 = grid.geometry.area / 1_000_000
    grid["population_density"] = grid["population_est"] / hex_area_km2
    return grid


def add_population_buffers(grid, boundaries, buffer_distances=(250, 500)):
    grid = grid.copy()
    context_area = grid.geometry.union_all().buffer(max(buffer_distances))
    context = select_population_context(boundaries, context_area)
    centres = grid.geometry.centroid

    for radius in buffer_distances:
        zones = grid[["hex_id", "geometry"]].copy()
        zones["geometry"] = centres.buffer(radius)
        population = allocate_population(zones, context)
        column = f"population_{radius}m"
        grid[column] = grid["hex_id"].map(population).fillna(0)
    return grid
