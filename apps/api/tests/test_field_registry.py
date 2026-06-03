from pwps_agent_api.fields.registry import load_default_field_registry
from pwps_agent_api.schemas import InferencePolicy


def test_default_registry_loads_mvp_field_groups_in_order() -> None:
    registry = load_default_field_registry()

    assert [target.group_name for target in registry.confirmation_queue()] == [
        "basic_condition_group",
        "consumable_group",
        "parameter_group",
        "thermal_group",
        "meta_group",
    ]


def test_default_registry_has_unique_fields_and_valid_group_references() -> None:
    registry = load_default_field_registry()

    assert len(registry.fields) == len(set(registry.fields))

    for group in registry.groups.values():
        for field_name in group.fields:
            assert field_name in registry.fields


def test_default_registry_marks_meta_fields_as_provided_only() -> None:
    registry = load_default_field_registry()
    meta_group = registry.get_group("meta_group")

    assert meta_group.fields
    assert {
        registry.get_field(field_name).inference_policy for field_name in meta_group.fields
    } == {InferencePolicy.PROVIDED_ONLY}
