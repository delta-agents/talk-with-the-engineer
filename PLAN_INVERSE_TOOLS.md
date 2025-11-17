# Plan: Inverse Hold Measure Calculation

## Problem Statement

**Current Hold Tool (Forward):**
- **Input:** Desired water level reduction (cm), delay days, return period
- **Output:** Required area (ha) and percentage of surface area needed

**Inverse Hold Tool (Desired):**
- **Input:** Available area (ha), delay days, return period  
- **Output:** Achievable water level reduction (cm)

## Dutch Question Translation

**Original Dutch:**
> "Als x ha beschikbaar is om water vast te houden, wat is dan verlaging van de waterstand bij een bui met een terugkeertijd van 1x per yy jaar?"

**English Translation:**
> "If x ha is available to hold water, what is the water level reduction for a rainfall event with a return period of 1x per yy years?"

## Current Hold Tool Analysis

### Key Variables in Current Implementation:
1. `factor` - Percentage of area used for holding (0.05 to 1.0)
2. `area_polder` - Area used for holding (m²)
3. `delta_h_m_critical_init` - Water level reduction achieved (m)
4. `input.days_to_hold_discharge` - Delay days
5. `input.return_period` - Return period for rainfall event

### Current Algorithm Flow:
1. Start with `factor = 0.05` (5% of area)
2. Calculate discharge for normal and delayed scenarios
3. Find cumulative discharge up to maximum
4. Calculate water level reduction
5. Check if reduction meets target (`delta_h_available`)
6. If not, increase factor by 0.05 and repeat
7. Stop when target is met or factor reaches 1.0

## Inverse Algorithm Design

### New Input Model: `InverseHoldInput`
```python
class InverseHoldInput(RainfallInput, WaterSystemInput):
    """
    Input model for Inverse Hold tool.
    """
    available_area_ha: float = Field(
        ...,
        description="Available area for holding water in hectares",
        gt=0,
        le=1000  # Reasonable upper limit
    )
    days_to_hold_discharge: int = Field(
        2,
        description="Number of extra days the water is held in the polder",
        gt=0,
        le=30  # Reasonable upper limit
    )
    # delta_h_available is removed - this is what we want to calculate
```

### New Output Model: `InverseHoldOutput`
```python
class InverseHoldOutput(EngineerBaseModel):
    data: Dict[str, Any] = Field(..., description="data dictionary")
    description: str = Field(..., description="Water level reduction achieved")
    water_level_reduction_cm: float = Field(..., description="Achievable water level reduction in cm")
    area_utilization_percentage: float = Field(..., description="Percentage of total area used")
```

### Inverse Algorithm Flow:

1. **Input Processing:**
   - Convert `available_area_ha` to `area_polder` (m²)
   - Calculate `factor = area_polder / input.area_m2`
   - Validate that `factor <= 1.0` and `available_area_ha > 0`
   - **Additional Validation:** Ensure `available_area_ha <= input.area_ha`

2. **Rainfall and Flow Calculation:**
   - Use existing `get_rainfall(input)` function
   - Use existing `get_held_discharge(input, rainfall_per_day)` function
   - This gives both normal and delayed flow scenarios

3. **Scenario Comparison:**
   - **Scenario A (Without holding):** Calculate water level rise with normal flow
   - **Scenario B (With holding):** Calculate water level rise with delayed flow
   - **Reduction = Scenario A - Scenario B**

4. **Water Level Reduction Calculation (Refined to Match Actual Implementation):**
   ```python
   # Calculate unaccounted flows
   unaccounted_flow = max(flow_per_day - input.discharge_capacity_mm_d, 0)
   unaccounted_flow_delayed = max(flow_per_day_delayed - input.discharge_capacity_mm_d, 0)

   # Calculate area-based discharges (matching actual implementation)
   area_polder = input.area_m2 * factor
   area_polder_delayed = input.area_m2 * (1 - factor)

   discharge_normal = (unaccounted_flow / 1000) * area_polder
   discharge_normal_delayed = (unaccounted_flow_delayed / 1000) * area_polder_delayed
   discharge_combined = np.add(discharge_normal, discharge_normal_delayed)

   # Calculate water level rise
   sum_up_to_max_discharge = np.sum(discharge_combined[:np.argmax(discharge_combined) + 1])
   area_open_water = input.area_m2 * (input.percentage_open_water / 100)
   sum_up_to_max_delta_h = sum_up_to_max_discharge / area_open_water

   # Calculate reduction achieved
   water_level_reduction_cm = sum_up_to_max_delta_h * 100
   ```

5. **Output Generation:**
   - Calculate area utilization percentage: `factor * 100`
   - Generate description with correct variables

### Key Differences from Current Tool:

| Aspect | Current Hold Tool | Inverse Hold Tool |
|--------|------------------|-------------------|
| **Input** | `delta_h_available` (target) | `available_area_ha` (constraint) |
| **Output** | Required area | Achievable water level reduction |
| **Algorithm** | Iterative search for factor | Direct calculation with given factor |
| **Validation** | Check if target is achievable | Check if area constraint is valid |

### Implementation Steps:

1. **Create Models:**
   - `InverseHoldInput` in `models/modelset_rules_of_thumb/hold.py`
   - `InverseHoldOutput` in same file

2. **Create Tool:**
   - `inverse_hold_tool` in `tools/toolset_rules_of_thumb/hold.py`
   - Reuse existing utility functions
   - Implement direct calculation instead of iterative search

3. **Create Router:**
   - Add route in `routers/tools_router_RulesOfThumb.py`

4. **Testing:**
   - Unit tests in `tests/src/tools/test_hold.py`
   - Integration tests

### Template Description Format:

**English:**
> "With {available_area_ha:.2f} ha available for holding water, using the 'holding' measure we can delay the water discharge by {days_to_hold_discharge} days, achieving a water level reduction of {water_level_reduction_cm:.1f} cm for a rainfall event with a return period of {return_period} years (utilizing {area_utilization_percentage:.1f}% of the total area)."

**Dutch:**
> "Met {available_area_ha:.2f} ha beschikbaar voor het vasthouden van water, kunnen we met maatregel 'vasthouden' de afvoer water {days_to_hold_discharge} dagen vertragen, waardoor een verlaging van de waterstand van {water_level_reduction_cm:.1f} cm wordt bereikt bij een bui met een terugkeertijd van {return_period} jaar (waarbij {area_utilization_percentage:.1f}% van het totale oppervlak wordt benut)."

### Error Handling:

1. **Input Validation:**
   - Ensure `available_area_ha > 0`
   - Ensure `available_area_ha <= total_area_ha`
   - Ensure `days_to_hold_discharge > 0`
   - Raise `ModelRetry` if constraints violated

2. **Edge Cases:**
   - Very small available area → minimal water level reduction
   - Available area = total area → maximum possible reduction
   - Negative water level reduction → return 0 (no benefit)
   - Invalid return period → use existing validation

3. **Error Messages:**
   - "Available area must be positive and not exceed total area"
   - "Available area cannot exceed total area"
   - "Days to hold discharge must be positive"
   - "No meaningful water level reduction achievable with given constraints"

### Dependencies:

- Reuse existing utility functions:
  - `get_rainfall()`
  - `get_held_discharge()`
- Reuse existing validation from base models
- Follow same logging pattern with `@log_tool_call`

This inverse calculation will complement the existing hold tool by allowing users to work backwards from available area constraints to determine achievable water level reductions.

---

# Plan: Inverse Store Measure Calculation (Inverse Bergen)

## Problem Statement

**Current Store Tool (Forward):**
- **Input:** Desired water level reduction (cm), return period
- **Output:** Required additional open water area (ha) and percentage of total area

**Inverse Store Tool (Desired):**
- **Input:** Available additional open water area (ha), return period
- **Output:** Achievable water level reduction (cm)

## Dutch Question Translation

**Original Dutch:**
> "Als het open water met x ha wordt uitgebreid, wat is dan verlaging van de waterstand bij een bui met een terugkeertijd van 1x per yy jaar?"

**English Translation:**
> "If the open water is expanded by x ha, what is the water level reduction for a rainfall event with a return period of 1x per yy years?"

## Current Store Tool Analysis

### Key Variables in Current Implementation:
1. `area_m2_current_open_water` - Current open water area (m²)
2. `area_m2_required_open_water` - Required additional open water area (m²)
3. `area_ha_required_open_water` - Required additional open water area (ha)
4. `input.delta_h_available` - Target water level reduction (m)
5. `sum_up_to_max_delta_h_m` - Total unaccounted flow volume (m³)

### Current Algorithm Flow:
1. Calculate current open water area from percentage
2. Calculate unaccounted flow (excess flow beyond discharge capacity)
3. Find cumulative unaccounted flow up to maximum
4. Calculate required additional open water area using formula:
   ```
   area_m2_required = area_m2_current * ((sum_up_to_max_delta_h_m - delta_h_available) / delta_h_available)
   ```

## Inverse Store Algorithm Design

### New Input Model: `InverseStoreInput`
```python
class InverseStoreInput(RainfallInput, WaterSystemInput):
    """
    Input model for Inverse Store tool.
    """
    additional_open_water_area_ha: float = Field(
        ...,
        description="Additional open water area available in hectares",
        ge=0,
        le=1000  # Reasonable upper limit
    )
    # delta_h_available is removed - this is what we want to calculate
```

### New Output Model: `InverseStoreOutput`
```python
class InverseStoreOutput(EngineerBaseModel):
    data: Dict[str, Any] = Field(..., description="data dictionary")
    description: str = Field(..., description="Water level reduction achieved")
    water_level_reduction_cm: float = Field(..., description="Achievable water level reduction in cm")
    total_open_water_percentage: float = Field(..., description="Total percentage of area as open water")
    additional_open_water_percentage: float = Field(..., description="Additional percentage of area as open water")
```

### Inverse Store Algorithm Flow:

1. **Input Processing:**
   - Convert `additional_open_water_area_ha` to `area_m2_additional` (m²)
   - Calculate new total open water area: `area_m2_new_open_water = area_m2_current + area_m2_additional`
   - Calculate new percentage: `new_percentage = area_m2_new_open_water / input.area_m2 * 100`
   - Validate that `additional_open_water_area_ha >= 0` and `new_percentage <= 100`
   - **Additional Validation:** Ensure `additional_open_water_area_ha <= input.area_ha * 0.5` (max 50% additional)

2. **Rainfall and Flow Calculation:**
   - Use existing `get_rainfall(input)` function
   - Use existing `get_discharge(input, rainfall_per_day)` function
   - Calculate `unaccounted_flow`

3. **Water Level Reduction Calculation (Corrected):**
   ```python
   # Calculate unaccounted flow with current discharge capacity
   unaccounted_flow = max(flow_per_day - input.discharge_capacity_mm_d, 0)
   total_unaccounted_flow = (unaccounted_flow / 1000) * input.area_m2
   sum_up_to_max_delta_h_m = np.sum(total_unaccounted_flow[:np.argmax(total_unaccounted_flow) + 1])

   # Calculate achievable reduction with additional storage
   # The additional storage can absorb the excess water
   water_level_reduction_cm = (sum_up_to_max_delta_h_m / area_m2_new_open_water) * 100
   ```

4. **Output Generation:**
   - Calculate current and new percentages for description
   - Generate description with correct variables

### Template Description Format:

**English:**
> "With {additional_open_water_area_ha:.2f} ha additional open water area available, using the 'storage' measure we can increase the open water surface area by {additional_open_water_area_ha:.2f} ha, to a total of {total_open_water_percentage:.1f}% of the area (was {current_open_water_percentage:.1f}%), achieving a water level reduction of {water_level_reduction_cm:.1f} cm for a rainfall event with a return period of {return_period} years."

**Template Variables:**
- `{additional_open_water_area_ha}` - From input
- `{total_open_water_percentage}` - Calculated: `(area_m2_current + area_m2_additional) / input.area_m2 * 100`
- `{current_open_water_percentage}` - Calculated: `input.percentage_open_water`
- `{water_level_reduction_cm}` - Calculated from algorithm
- `{return_period}` - From input

**Dutch:**
> "Met {additional_open_water_area_ha:.2f} ha extra open water oppervlakte beschikbaar, kunnen we met maatregel 'bergen' het open water oppervlakte uitbreiden met {additional_open_water_area_ha:.2f} ha, tot een totaal van {total_open_water_percentage:.1f}% van het gebied (was {current_open_water_percentage:.1f}%), waardoor een verlaging van de waterstand van {water_level_reduction_cm:.1f} cm wordt bereikt bij een bui met een terugkeertijd van {return_period} jaar."

### Error Handling:

1. **Input Validation:**
   - Ensure `additional_open_water_area_ha >= 0`
   - Ensure new total percentage doesn't exceed 100%
   - Raise `ModelRetry` if constraints violated

2. **Edge Cases:**
   - Zero additional area → no water level reduction
   - Very large additional area → maximum possible reduction
   - Negative water level reduction → return 0 (no benefit)

3. **Error Messages:**
   - "Additional open water area must be non-negative"
   - "Total open water percentage cannot exceed 100%"
   - "Additional open water area exceeds reasonable limits (max 50% of total area)"
   - "No meaningful water level reduction achievable with given constraints"

---

# Plan: Inverse Discharge Measure Calculation (Inverse Afvoer)

## Problem Statement

**Current Discharge Tool (Forward):**
- **Input:** Desired water level reduction (cm), return period
- **Output:** Required additional discharge capacity (m³/min) and total capacity

**Inverse Discharge Tool (Desired):**
- **Input:** Available additional discharge capacity (m³/min), return period
- **Output:** Achievable water level reduction (cm)

## Dutch Question Translation

**Original Dutch:**
> "Als de afvoercapaciteit met x m3/min wordt uitgebreid, wat is dan verlaging van de waterstand bij een bui met een terugkeertijd van 1x per yy jaar?"

**English Translation:**
> "If the discharge capacity is expanded by x m³/min, what is the water level reduction for a rainfall event with a return period of 1x per yy years?"

## Current Discharge Tool Analysis

### Key Variables in Current Implementation:
1. `extra_discharge_capacity_m3_d_required` - Required additional discharge capacity (m³/d)
2. `extra_discharge_capacity_m3_per_min_required` - Required additional discharge capacity (m³/min)
3. `total_discharge_capactiy_m3_per_min` - Total discharge capacity (m³/min)
4. `input.delta_h_available` - Target water level reduction (m)
5. `n_days_excess_flow` - Number of days with excess flow

### Current Algorithm Flow:
1. Calculate unaccounted flow (excess flow beyond current discharge capacity)
2. Find cumulative unaccounted flow up to maximum
3. Calculate required additional discharge capacity using formula:
   ```
   extra_discharge_capacity = ((sum_up_to_max_delta_h_m / area_open_water) - delta_h_available) * area_open_water / n_days_excess_flow
   ```

## Inverse Discharge Algorithm Design

### New Input Model: `InverseDischargeInput`
```python
class InverseDischargeInput(RainfallInput, WaterSystemInput):
    """
    Input model for Inverse Discharge tool.
    """
    additional_discharge_capacity_m3_per_min: float = Field(
        ...,
        description="Additional discharge capacity available in m³/min",
        ge=0,
        le=1000  # Reasonable upper limit
    )
    # delta_h_available is removed - this is what we want to calculate
```

### New Output Model: `InverseDischargeOutput`
```python
class InverseDischargeOutput(EngineerBaseModel):
    data: Dict[str, Any] = Field(..., description="data dictionary")
    description: str = Field(..., description="Water level reduction achieved")
    water_level_reduction_cm: float = Field(..., description="Achievable water level reduction in cm")
    total_discharge_capacity_m3_per_min: float = Field(..., description="Total discharge capacity in m³/min")
    total_discharge_capacity_mm_per_day: float = Field(..., description="Total discharge capacity in mm/day")
```

### Inverse Discharge Algorithm Flow:

1. **Input Processing:**
   - Convert `additional_discharge_capacity_m3_per_min` to various units
   - Calculate new total discharge capacity: `total_capacity = current_capacity + additional_capacity`
   - Update discharge capacity in input for calculations
   - Validate that `additional_discharge_capacity_m3_per_min >= 0`
   - **Additional Validation:** Ensure reasonable capacity limits (max 1 cm/day equivalent)

2. **Rainfall and Flow Calculation:**
   - Use existing `get_rainfall(input)` function
   - Use existing `get_discharge(input, rainfall_per_day)` function with updated capacity
   - Calculate `unaccounted_flow` with new total capacity

3. **Water Level Reduction Calculation (Corrected with Verified Unit Conversions):**
   ```python
   # Calculate new total discharge capacity
   new_discharge_capacity_m3_per_min = input.discharge_capacity_m3_per_min + input.additional_discharge_capacity_m3_per_min

   # Convert to mm/day (verified unit conversion)
   # m3/min * 60 min/h * 24 h/d = m3/d
   # m3/d / m2 * 1000 mm/m = mm/d
   new_discharge_capacity_mm_d = new_discharge_capacity_m3_per_min * 60 * 24 / input.area_m2 * 1000

   # Calculate unaccounted flow with new capacity
   unaccounted_flow = max(flow_per_day - new_discharge_capacity_mm_d, 0)
   total_unaccounted_flow = (unaccounted_flow / 1000) * input.area_m2
   sum_up_to_max_delta_h_m = np.sum(total_unaccounted_flow[:np.argmax(total_unaccounted_flow) + 1])

   # Calculate achievable reduction
   area_open_water = input.area_m2 * (input.percentage_open_water / 100)
   water_level_reduction_cm = (sum_up_to_max_delta_h_m / area_open_water) * 100
   ```

4. **Output Generation:**
   - Calculate total capacities in different units
   - Generate description with correct variables

### Template Description Format:

**English:**
> "With {additional_discharge_capacity_m3_per_min:.2f} m³/min additional discharge capacity available, using the 'discharge' measure we can increase the discharge capacity by {additional_discharge_capacity_m3_per_min:.2f} m³/min, to a total of {total_discharge_capacity_m3_per_min:.2f} m³/min (this total is then {total_discharge_capacity_mm_per_day:.1f} mm/day), achieving a water level reduction of {water_level_reduction_cm:.1f} cm for a rainfall event with a return period of {return_period} years."

**Template Variables:**
- `{additional_discharge_capacity_m3_per_min}` - From input
- `{total_discharge_capacity_m3_per_min}` - Calculated: `input.discharge_capacity_m3_per_min + input.additional_discharge_capacity_m3_per_min`
- `{total_discharge_capacity_mm_per_day}` - Calculated: `total_discharge_capacity_m3_per_min * 60 * 24 / input.area_m2 * 1000` (verified unit conversion)
- `{water_level_reduction_cm}` - Calculated from algorithm
- `{return_period}` - From input

**Dutch:**
> "Met {additional_discharge_capacity_m3_per_min:.2f} m³/min extra afvoercapaciteit beschikbaar, kunnen we met maatregel 'afvoeren' de afvoercapaciteit vergroten met {additional_discharge_capacity_m3_per_min:.2f} m³/min, tot een totaal van {total_discharge_capacity_m3_per_min:.2f} m³/min (dit totaal is dan {total_discharge_capacity_mm_per_day:.1f} mm/dag), waardoor een verlaging van de waterstand van {water_level_reduction_cm:.1f} cm wordt bereikt bij een bui met een terugkeertijd van {return_period} jaar."

### Error Handling:

1. **Input Validation:**
   - Ensure `additional_discharge_capacity_m3_per_min >= 0`
   - Ensure new total capacity is reasonable (not excessive)
   - Raise `ModelRetry` if constraints violated

2. **Edge Cases:**
   - Zero additional capacity → no water level reduction
   - Very large additional capacity → maximum possible reduction
   - Negative water level reduction → return 0 (no benefit)

3. **Error Messages:**
   - "Additional discharge capacity must be non-negative"
   - "Total discharge capacity exceeds reasonable limits"
   - "Additional discharge capacity exceeds reasonable limits (max 1 cm/day equivalent)"
   - "No meaningful water level reduction achievable with given constraints"

---

# Implementation Summary

## All Three Inverse Tools:

### Common Implementation Steps:

1. **Create Models:**
   - `InverseHoldInput/Output` in `models/modelset_rules_of_thumb/hold.py`
   - `InverseStoreInput/Output` in `models/modelset_rules_of_thumb/store.py`
   - `InverseDischargeInput/Output` in `models/modelset_rules_of_thumb/discharge.py`

2. **Create Tools:**
   - `inverse_hold_tool` in `tools/toolset_rules_of_thumb/hold.py`
   - `inverse_store_tool` in `tools/toolset_rules_of_thumb/store.py`
   - `inverse_discharge_tool` in `tools/toolset_rules_of_thumb/discharge.py`

3. **Create Router:**
   - Add routes in `routers/tools_router_RulesOfThumb.py`

4. **Testing:**
   - Unit tests for each tool
   - Integration tests

### Key Differences Between Tools:

| Tool | Input Constraint | Calculation Method | Key Formula |
|------|------------------|-------------------|-------------|
| **Inverse Hold** | Available area (ha) | Area-based discharge calculation | `discharge_combined = normal + delayed` |
| **Inverse Store** | Additional open water area (ha) | Direct calculation with new storage area | `delta_h = sum_discharge / new_open_water_area` |
| **Inverse Discharge** | Additional discharge capacity (m³/min) | Recalculate with new capacity | `delta_h = sum_discharge / area_open_water` |

### Critical Implementation Notes:

1. **Inverse Hold Tool**: Uses area-based discharge calculation matching actual implementation logic
2. **Inverse Store Tool**: Calculates reduction based on additional storage capacity
3. **Inverse Discharge Tool**: Calculates reduction based on increased discharge capacity with verified unit conversions
4. **All Tools**: Include comprehensive input validation, reasonable limits, and error handling

### Error Handling for All Tools:

1. **Constraint Validation:**
   - Hold: Ensure `available_area_ha <= total_area_ha`
   - Store: Ensure `additional_area_ha >= 0` and reasonable limits
   - Discharge: Ensure `additional_capacity >= 0` and reasonable limits

2. **Edge Cases:**
   - Very small constraints → minimal water level reduction
   - Very large constraints → maximum possible reduction
   - Invalid return periods → use existing validation

These inverse calculations will complement all existing tools by allowing users to work backwards from resource constraints to determine achievable water level reductions.

---

## Implementation Readiness

### Technical Specifications

The plan includes comprehensive technical specifications for all three inverse tools:

- **Mathematical Algorithms**: Area-based discharge calculations matching actual implementation logic
- **Input Validation**: Pydantic constraints with reasonable limits and comprehensive error handling
- **Template Variables**: Complete variable definitions with calculation methods and verified unit conversions
- **Error Handling**: Edge case management with clear error messages and constraint validation

### Quality Assurance

- **Code Reuse**: Leverages existing utility functions (`get_rainfall`, `get_discharge`, `get_held_discharge`)
- **Validation**: Comprehensive input validation with reasonable limits for all parameters
- **Documentation**: Complete bilingual support (Dutch/English) with clear variable specifications
- **Testing**: Unit and integration test specifications included

### Implementation Timeline

1. **Phase 1**: Create input/output models with validation
2. **Phase 2**: Implement inverse calculation algorithms
3. **Phase 3**: Add router integration and error handling
4. **Phase 4**: Unit testing and validation
5. **Phase 5**: Integration testing and deployment

**Status**: Ready for implementation
