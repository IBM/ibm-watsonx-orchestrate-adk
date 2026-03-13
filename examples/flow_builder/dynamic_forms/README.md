# Dynamic Forms Example

This example demonstrates advanced dynamic form capabilities in watsonx Orchestrate, including:

- **Label Behaviour**: Change field labels based on other field values
- **Visibility Behaviour**: Show/hide fields conditionally  
- **Value-Source Behaviour**: Populate field options dynamically from tools
- **RuleBuilder API**: Simplified rule creation without JSON Schema knowledge

## Features Demonstrated

### 1. Label Changes
When the country field changes, labels update automatically:
- "Zip code" vs "Postal code" based on country selection
- "State" vs "Province" based on country selection
- "US W-2 Form" vs "Canadian T4 Form" for document upload

### 2. Conditional Visibility
Fields appear or disappear based on selections:
- City field only visible when USA is selected
- URL field only visible when Canada is selected

### 3. Dynamic Value Population
Field options are populated from tools:
- Region dropdown populated from `get_states_or_provinces` tool
- Options change automatically when country changes (US states vs Canadian provinces)

## Files

- **tools/user_activity_with_dynamic_forms_full.py** - Main flow definition using RuleBuilder
- **tools/get_states_or_provinces.py** - Supporting Python tool that returns region data based on country
  - **Purpose**: Demonstrates value-source behaviour by dynamically populating the region dropdown
  - **Input**: Takes a country parameter ("USA" or "Canada")
  - **Output**: Returns a list of US states or Canadian provinces
  - **Requirements**: Must be synchronous, no context variables, returns list of strings
- **agents/user_activity_agent_dynamic_forms.yaml** - Agent configuration
- **import-all.sh** - Import script for tools and agent
- **main.py** - Script to build and save the flow
- **generated/** - Output folder for generated flow JSON

## Usage

### Option 1: Test with Agent (Recommended)

1. To test this example, make sure the Flow runtime is activated.
2. Run `import-all.sh` 
3. Launch the Chat UI with `orchestrate chat start`
4. Pick the `user_activity_dynamic_forms_agent`
5. Type in something like `Dynamic form`. Then, the agent will prompt you for inputs

### Option 2: Build Flow Programmatically

1. Set PYTHONPATH:
   ```bash
   export PYTHONPATH=/path/to/wxo-clients/src:/path/to/wxo-clients
   ```
2. Run the main script:
   ```bash
   python3 main.py
   ```
3. Check `generated/flow_with_dynamic_forms_full.json` for output

## Key Code Examples

### Using RuleBuilder for Label Changes

Instead of complex JSON Schema conditions, use the simplified RuleBuilder API:

```python
from ibm_watsonx_orchestrate.flow_builder.utils import RuleBuilder

form_node.label_behaviour_field(
    name="label_behaviour",
    on_change_to_field="country",
    rules=[
        RuleBuilder.label_rule(
            field_name="country",
            field_value="USA",
            impacted_field="code",
            label_when_true="Zip code",
            label_when_false="Postal code",
            operator="equals"
        )
    ]
)
```

### Using RuleBuilder for Visibility

```python
form_node.visibility_behaviour_field(
    name="visibility_behaviour",
    on_change_to_field="country",
    rules=[
        RuleBuilder.visibility_rule(
            field_name="country",
            field_value="USA",
            impacted_field="city",
            visible_when_true=True,
            operator="equals"
        )
    ]
)
```

### Parameter Requirements

#### RuleBuilder.visibility_rule()

**Mandatory Parameters:**
- `field_name` (str) - The field to monitor for changes
- `field_value` (Any) - The value to check against
- `impacted_field` (str) - The field whose visibility will be controlled
- `operator` (str) - Comparison operator (see table below)

**Optional Parameters:**
- `visible_when_true` (bool) - Default: `True`
  - `True` = Show field when condition matches
  - `False` = Hide field when condition matches

#### RuleBuilder.label_rule()

**Mandatory Parameters (all required):**
- `field_name` (str) - The field to monitor for changes
- `field_value` (Any) - The value to check against
- `impacted_field` (str) - The field whose label will change
- `operator` (str) - Comparison operator (see table below)
- `label_when_true` (str) - Label when condition matches
- `label_when_false` (str) - Label when condition doesn't match

### Supported Operators

RuleBuilder supports the following comparison operators:

| Operator | Description | Use Case | Example |
|----------|-------------|----------|---------|
| `equals` | Exact match (==) | Show field when country equals "USA" | String/number equality |
| `not_equals` | Not equal (!=) | Show field when country is NOT "USA" | Inverse conditions |
| `minimum` | Greater than or equal (>=) | Show field when age >= 18 | Numeric comparisons |
| `maximum` | Less than or equal (<=) | Show field when age <= 65 | Numeric comparisons |

**Examples with different operators:**

```python
# Not equals operator - show field when country is NOT USA
RuleBuilder.visibility_rule(
    field_name="country",
    field_value="USA",
    impacted_field="international_shipping",
    visible_when_true=True,
    operator="not_equals"
)

# Minimum operator - show field when age >= 18
RuleBuilder.visibility_rule(
    field_name="age",
    field_value=18,
    impacted_field="adult_content",
    visible_when_true=True,
    operator="minimum"
)

# Maximum operator - change label when age <= 65
RuleBuilder.label_rule(
    field_name="age",
    field_value=65,
    impacted_field="discount_type",
    label_when_true="Senior Discount",
    label_when_false="Regular Price",
    operator="maximum"
)
```

### Using Simplified Value-Source API

```python
form_node.value_source_behaviour_field(
    name="value_source_behaviour",
    on_change_to_field="country",
    impacted_field="region",
    tool_name="get_states_or_provinces",
    tool_id="9f0ecb53-dbd9-4e41-be46-29c8d47d6df8",
    field_mappings={
        "country": "parent.field.country"
    }
)

## Tool Requirements for Value-Source Behaviour

The `get_states_or_provinces` tool demonstrates the requirements for tools used in value-source behaviours:

- **List output**: Dropdown fields require a list of options to display
