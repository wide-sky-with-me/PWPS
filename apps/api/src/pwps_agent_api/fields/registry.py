from pydantic import BaseModel, ConfigDict, model_validator

from pwps_agent_api.schemas import (
    ConfirmationPolicy,
    FieldGroupSpec,
    FieldSpec,
    FieldTarget,
    FieldType,
    InferencePolicy,
)

FIELD_REGISTRY_VERSION = "1.0.0"


class FieldRegistry(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    fields: dict[str, FieldSpec]
    groups: dict[str, FieldGroupSpec]
    field_registry_version: str = FIELD_REGISTRY_VERSION

    @model_validator(mode="after")
    def validate_group_references(self) -> "FieldRegistry":
        missing_fields: dict[str, list[str]] = {}
        for group_name, group in self.groups.items():
            unknown = [field_name for field_name in group.fields if field_name not in self.fields]
            if unknown:
                missing_fields[group_name] = unknown

        if missing_fields:
            raise ValueError(f"field groups reference unknown fields: {missing_fields}")

        return self

    def get_field(self, name: str) -> FieldSpec:
        return self.fields[name]

    def get_group(self, name: str) -> FieldGroupSpec:
        return self.groups[name]

    def confirmation_queue(self) -> list[FieldTarget]:
        ordered_groups = sorted(
            self.groups.values(),
            key=lambda group: (group.confirmation_order, group.name),
        )
        return [
            FieldTarget(
                group_name=group.name,
                fields=group.fields,
                reason=f"Confirm {group.label} fields for pWPS draft generation.",
                priority=group.confirmation_order,
            )
            for group in ordered_groups
        ]


def load_default_field_registry() -> FieldRegistry:
    fields = _default_fields()
    groups = _default_groups()
    return FieldRegistry(fields=fields, groups=groups)


def _field(
    *,
    name: str,
    label: str,
    group: str,
    field_type: FieldType,
    description: str,
    required_for_start: bool = False,
    required_for_draft: bool = True,
    high_risk: bool = False,
    inference_policy: InferencePolicy = InferencePolicy.MODEL_ALLOWED,
    confirmation_policy: ConfirmationPolicy = ConfirmationPolicy.CONFIRM_IF_LOW_EVIDENCE,
    dependencies: list[str] | None = None,
    affects: list[str] | None = None,
    unit: str | None = None,
    enum_values: list[str] | None = None,
    audit_rules: list[str] | None = None,
    candidate_strategy: str | None = None,
    output_section: str | None = None,
    examples: list[str] | None = None,
) -> FieldSpec:
    return FieldSpec(
        name=name,
        label=label,
        group=group,
        field_type=field_type,
        description=description,
        unit=unit,
        enum_values=enum_values or [],
        required_for_start=required_for_start,
        required_for_draft=required_for_draft,
        high_risk=high_risk,
        inference_policy=inference_policy,
        confirmation_policy=confirmation_policy,
        dependencies=dependencies or [],
        affects=affects or [],
        output_section=output_section,
        audit_rules=audit_rules or [],
        candidate_strategy=candidate_strategy,
        examples=examples or [],
        field_registry_version=FIELD_REGISTRY_VERSION,
    )


def _default_fields() -> dict[str, FieldSpec]:
    specs = [
        _field(
            name="base_material",
            label="母材",
            group="basic_condition_group",
            field_type=FieldType.STRING,
            description="Base material or material grade provided by the user.",
            required_for_start=True,
            affects=["consumable", "preheat_temperature", "pwht"],
            output_section="base_material",
            examples=["Q345R", "Q235B"],
        ),
        _field(
            name="thickness",
            label="厚度",
            group="basic_condition_group",
            field_type=FieldType.DIMENSION,
            description="Base material thickness for the joint.",
            unit="mm",
            required_for_start=True,
            affects=["current_range", "voltage_range", "travel_speed", "heat_input"],
            output_section="base_material",
            examples=["12mm"],
        ),
        _field(
            name="welding_process",
            label="焊法",
            group="basic_condition_group",
            field_type=FieldType.ENUM,
            description="Welding process used for the draft.",
            enum_values=["GMAW", "SMAW", "GTAW", "SAW"],
            required_for_start=True,
            affects=["consumable", "shielding_gas", "polarity"],
            output_section="process",
            audit_rules=["process_consumable_match"],
            examples=["GMAW"],
        ),
        _field(
            name="joint_type",
            label="接头形式",
            group="basic_condition_group",
            field_type=FieldType.STRING,
            description="Joint type such as butt joint or fillet joint.",
            required_for_start=True,
            output_section="joint",
            examples=["对接焊"],
        ),
        _field(
            name="welding_position",
            label="焊接位置",
            group="basic_condition_group",
            field_type=FieldType.ENUM,
            description="Welding position used for the draft.",
            enum_values=["flat", "horizontal", "vertical", "overhead"],
            required_for_start=True,
            output_section="position",
            examples=["平焊"],
        ),
        _field(
            name="consumable",
            label="焊材",
            group="consumable_group",
            field_type=FieldType.STRING,
            description="Welding consumable or filler metal.",
            high_risk=True,
            dependencies=["base_material", "welding_process"],
            affects=["current_range", "voltage_range"],
            audit_rules=["process_consumable_match"],
            candidate_strategy="match_process_and_material",
            output_section="consumable",
            examples=["ER50-6"],
        ),
        _field(
            name="consumable_specification",
            label="焊材规格",
            group="consumable_group",
            field_type=FieldType.DIMENSION,
            description="Consumable diameter or specification.",
            unit="mm",
            dependencies=["consumable", "welding_process"],
            affects=["current_range", "voltage_range"],
            output_section="consumable",
            examples=["1.2mm"],
        ),
        _field(
            name="shielding_gas",
            label="保护气体",
            group="consumable_group",
            field_type=FieldType.STRING,
            description="Shielding gas for processes that require it.",
            dependencies=["welding_process"],
            output_section="consumable",
            examples=["Ar+CO2"],
        ),
        _field(
            name="current_range",
            label="电流",
            group="parameter_group",
            field_type=FieldType.RANGE,
            description="Recommended welding current range.",
            unit="A",
            high_risk=True,
            inference_policy=InferencePolicy.EVIDENCE_REQUIRED,
            confirmation_policy=ConfirmationPolicy.ALWAYS_CONFIRM,
            dependencies=["thickness", "welding_process", "consumable_specification"],
            affects=["heat_input"],
            audit_rules=["parameter_completeness", "heat_input_consistency"],
            output_section="parameters",
        ),
        _field(
            name="voltage_range",
            label="电压",
            group="parameter_group",
            field_type=FieldType.RANGE,
            description="Recommended welding voltage range.",
            unit="V",
            high_risk=True,
            inference_policy=InferencePolicy.EVIDENCE_REQUIRED,
            confirmation_policy=ConfirmationPolicy.ALWAYS_CONFIRM,
            dependencies=["welding_process", "consumable_specification"],
            affects=["heat_input"],
            audit_rules=["parameter_completeness", "heat_input_consistency"],
            output_section="parameters",
        ),
        _field(
            name="travel_speed",
            label="焊接速度",
            group="parameter_group",
            field_type=FieldType.RANGE,
            description="Recommended travel speed range.",
            unit="cm/min",
            high_risk=True,
            inference_policy=InferencePolicy.EVIDENCE_REQUIRED,
            confirmation_policy=ConfirmationPolicy.ALWAYS_CONFIRM,
            dependencies=["welding_process", "thickness"],
            affects=["heat_input"],
            audit_rules=["parameter_completeness", "heat_input_consistency"],
            output_section="parameters",
        ),
        _field(
            name="heat_input",
            label="热输入",
            group="parameter_group",
            field_type=FieldType.RANGE,
            description="Derived heat input range.",
            unit="kJ/mm",
            high_risk=True,
            inference_policy=InferencePolicy.DERIVED,
            confirmation_policy=ConfirmationPolicy.ALWAYS_CONFIRM,
            dependencies=["current_range", "voltage_range", "travel_speed"],
            audit_rules=["heat_input_consistency"],
            output_section="parameters",
        ),
        _field(
            name="polarity",
            label="极性",
            group="parameter_group",
            field_type=FieldType.STRING,
            description="Welding current polarity.",
            dependencies=["welding_process", "consumable"],
            output_section="parameters",
        ),
        _field(
            name="preheat_temperature",
            label="预热温度",
            group="thermal_group",
            field_type=FieldType.TEMPERATURE,
            description="Preheat temperature requirement.",
            unit="degC",
            high_risk=True,
            inference_policy=InferencePolicy.EVIDENCE_REQUIRED,
            confirmation_policy=ConfirmationPolicy.ALWAYS_CONFIRM,
            dependencies=["base_material", "thickness"],
            audit_rules=["thermal_evidence_required"],
            output_section="thermal",
        ),
        _field(
            name="interpass_temperature",
            label="层间温度",
            group="thermal_group",
            field_type=FieldType.TEMPERATURE,
            description="Maximum or controlled interpass temperature.",
            unit="degC",
            high_risk=True,
            inference_policy=InferencePolicy.EVIDENCE_REQUIRED,
            confirmation_policy=ConfirmationPolicy.ALWAYS_CONFIRM,
            dependencies=["base_material", "thickness", "welding_process"],
            audit_rules=["thermal_evidence_required"],
            output_section="thermal",
        ),
        _field(
            name="pwht",
            label="焊后热处理",
            group="thermal_group",
            field_type=FieldType.TEXT,
            description="Post-weld heat treatment requirement or restriction.",
            high_risk=True,
            inference_policy=InferencePolicy.EVIDENCE_REQUIRED,
            confirmation_policy=ConfirmationPolicy.ALWAYS_CONFIRM,
            dependencies=["base_material", "thickness"],
            audit_rules=["thermal_evidence_required"],
            output_section="thermal",
        ),
        _field(
            name="project_name",
            label="项目名称",
            group="meta_group",
            field_type=FieldType.STRING,
            description="Project name. The model must not invent this value.",
            required_for_draft=False,
            inference_policy=InferencePolicy.PROVIDED_ONLY,
            confirmation_policy=ConfirmationPolicy.NEVER_INFER,
            output_section="meta",
        ),
        _field(
            name="client_name",
            label="客户名称",
            group="meta_group",
            field_type=FieldType.STRING,
            description="Client name. The model must not invent this value.",
            required_for_draft=False,
            inference_policy=InferencePolicy.PROVIDED_ONLY,
            confirmation_policy=ConfirmationPolicy.NEVER_INFER,
            output_section="meta",
        ),
        _field(
            name="document_number",
            label="文件编号",
            group="meta_group",
            field_type=FieldType.STRING,
            description="Document number. The model must not invent this value.",
            required_for_draft=False,
            inference_policy=InferencePolicy.PROVIDED_ONLY,
            confirmation_policy=ConfirmationPolicy.NEVER_INFER,
            output_section="meta",
        ),
    ]

    return {spec.name: spec for spec in specs}


def _group(
    *,
    name: str,
    label: str,
    description: str,
    fields: list[str],
    required_fields: list[str] | None = None,
    optional_fields: list[str] | None = None,
    depends_on_groups: list[str] | None = None,
    confirmation_order: int,
) -> FieldGroupSpec:
    return FieldGroupSpec(
        name=name,
        label=label,
        description=description,
        fields=fields,
        required_fields=required_fields or [],
        optional_fields=optional_fields or [],
        depends_on_groups=depends_on_groups or [],
        confirmation_order=confirmation_order,
    )


def _default_groups() -> dict[str, FieldGroupSpec]:
    groups = [
        _group(
            name="basic_condition_group",
            label="基础条件",
            description=(
                "Confirm base material, thickness, welding process, joint type, and position."
            ),
            fields=[
                "base_material",
                "thickness",
                "welding_process",
                "joint_type",
                "welding_position",
            ],
            required_fields=[
                "base_material",
                "thickness",
                "welding_process",
                "joint_type",
                "welding_position",
            ],
            confirmation_order=10,
        ),
        _group(
            name="consumable_group",
            label="焊材与保护",
            description="Confirm consumable, consumable specification, and shielding gas.",
            fields=["consumable", "consumable_specification", "shielding_gas"],
            required_fields=["consumable"],
            optional_fields=["consumable_specification", "shielding_gas"],
            depends_on_groups=["basic_condition_group"],
            confirmation_order=20,
        ),
        _group(
            name="parameter_group",
            label="焊接参数",
            description="Confirm current, voltage, travel speed, heat input, and polarity.",
            fields=["current_range", "voltage_range", "travel_speed", "heat_input", "polarity"],
            required_fields=["current_range", "voltage_range", "travel_speed"],
            optional_fields=["heat_input", "polarity"],
            depends_on_groups=["basic_condition_group", "consumable_group"],
            confirmation_order=30,
        ),
        _group(
            name="thermal_group",
            label="热过程",
            description="Confirm preheat, interpass temperature, and post-weld heat treatment.",
            fields=["preheat_temperature", "interpass_temperature", "pwht"],
            optional_fields=["preheat_temperature", "interpass_temperature", "pwht"],
            depends_on_groups=["basic_condition_group"],
            confirmation_order=40,
        ),
        _group(
            name="meta_group",
            label="文档元信息",
            description="Record user-provided metadata without model inference.",
            fields=["project_name", "client_name", "document_number"],
            optional_fields=["project_name", "client_name", "document_number"],
            confirmation_order=50,
        ),
    ]

    return {group.name: group for group in groups}
