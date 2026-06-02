import pytest

from recycle_cost.manufacturing import (
    manufacturing_cell_cost_summary,
    manufacturing_cell_energy_consumption,
    manufacturing_cell_energy_inputs_calculated,
    manufacturing_cell_environment_summary,
    manufacturing_cell_material_composition,
    manufacturing_cell_material_cost,
    manufacturing_cell_material_inputs,
    manufacturing_cell_material_inputs_calculated,
    manufacturing_cell_size,
    manufacturing_cell_yields,
    manufacturing_general_inputs,
    manufacturing_module_component_masses,
    manufacturing_pack_component_masses,
    manufacturing_pack_environment_summary,
    manufacturing_pack_mass_summary,
    manufacturing_recycled_environment_totals_calculated,
    manufacturing_recycled_material_burdens_calculated,
    manufacturing_recycled_cathode_material_costs,
    manufacturing_recycled_cathode_material_environment,
)


def test_virgin_cell_manufacturing_snapshot_tables_default():
    inputs = manufacturing_general_inputs().set_index("item")
    size = manufacturing_cell_size().set_index("item")
    composition = manufacturing_cell_material_composition().set_index("material")
    energy = manufacturing_cell_energy_consumption().set_index("item")
    yields = manufacturing_cell_yields().set_index("item")

    assert inputs.loc["throughput", "value"] == pytest.approx(159632.0400050314)
    assert inputs.loc["cathode_chemistry", "value"] == "NMC(622)"
    assert size.loc["Cell mass (kg)", "Selected"] == pytest.approx(0.798160200025157)
    assert composition.loc["Active cathode material", "Selected"] == pytest.approx(0.44781830538476713)
    assert energy.loc["Total energy consumption (MJ/kg cell)", "Selected"] == pytest.approx(53.20203888725798)
    assert yields.loc["Cell accepted after testing (%)", "selected"] == pytest.approx(0.95)


def test_virgin_cell_manufacturing_calculation_snapshots_default():
    material_inputs = manufacturing_cell_material_inputs().set_index("material")
    environment = manufacturing_cell_environment_summary().set_index("metric")
    material_cost = manufacturing_cell_material_cost().set_index("item")
    cost_summary = manufacturing_cell_cost_summary().set_index("item")

    assert material_inputs.loc["Active cathode material", "kg_per_kg_cell"] == pytest.approx(0.5113862513445555)
    assert material_inputs.loc["NMP", "kg_per_kg_cell"] == pytest.approx(0.1704620837815185)
    assert material_inputs.loc["Binder (anode)", "kg_per_kg_cell"] == pytest.approx(0.006320707451316966)
    assert environment.loc["GHGs", "total"] == pytest.approx(20911.065890068643)
    assert material_cost.loc["Total", "cost_per_kg_cell"] == pytest.approx(20.81535117948296)
    assert cost_summary.loc["Total", "value"] == pytest.approx(29.291984173376168)


def test_cell_material_inputs_calculated_match_workbook_default():
    virgin = manufacturing_cell_material_inputs_calculated()
    recycled = manufacturing_cell_material_inputs_calculated("recycled")

    assert virgin.set_index("material").loc["NMP", "calculated_kg_per_kg_cell"] == pytest.approx(0.1704620837815185)
    assert recycled.set_index("material").loc["NMP", "calculated_kg_per_kg_cell"] == pytest.approx(0.1461696393046323)
    assert virgin["delta"].abs().max() == pytest.approx(0.0, abs=1e-12)
    assert recycled["delta"].abs().max() == pytest.approx(0.0, abs=1e-12)


def test_cell_energy_inputs_calculated_match_workbook_default():
    virgin = manufacturing_cell_energy_inputs_calculated().set_index("metric")
    recycled = manufacturing_cell_energy_inputs_calculated("recycled").set_index("metric")

    assert virgin.loc["Total Energy", "calculated_energy_inputs"] == pytest.approx(0.06464867367944649)
    assert virgin.loc["GHGs", "calculated_energy_inputs"] == pytest.approx(4262.608434543971)
    assert recycled.loc["Total Energy", "calculated_energy_inputs"] == pytest.approx(0.06787769531209299)
    assert recycled.loc["GHGs", "calculated_energy_inputs"] == pytest.approx(4870.282574646124)
    assert virgin["delta"].abs().max() == pytest.approx(0.0, abs=1e-9)
    assert recycled["delta"].abs().max() == pytest.approx(0.0, abs=1e-9)


def test_recycled_material_burdens_calculated_match_workbook_default():
    burdens = manufacturing_recycled_material_burdens_calculated().set_index("metric")

    assert burdens.loc["Total Energy", "calculated_material_pyro"] == pytest.approx(0.21841752910993853)
    assert burdens.loc["Water consumption (gal/kg cell)", "calculated_material_direct"] == pytest.approx(
        17.47897623628362
    )
    assert burdens.loc["GHGs", "calculated_material_direct"] == pytest.approx(16525.656692360524)


def test_recycled_environment_totals_calculated_match_workbook_default():
    totals = manufacturing_recycled_environment_totals_calculated().set_index("metric")

    assert totals.loc["Total Energy", "calculated_total_pyro"] == pytest.approx(0.2862952244220315)
    assert totals.loc["Water consumption (gal/kg cell)", "calculated_total_direct"] == pytest.approx(20.616524383404373)
    assert totals.loc["GHGs", "calculated_total_direct"] == pytest.approx(21395.939267006648)


def test_virgin_pack_manufacturing_snapshot_tables_default():
    module_masses = manufacturing_module_component_masses().set_index("component")
    pack_masses = manufacturing_pack_component_masses().set_index("component")
    pack_mass = manufacturing_pack_mass_summary().set_index("item")
    pack_environment = manufacturing_pack_environment_summary().set_index("metric")

    assert module_masses.loc["Cell interconnect", "Selected"] == pytest.approx(338.95202171794017)
    assert pack_masses.loc["Row rack", "Selected"] == pytest.approx(45.72267318611862)
    assert pack_mass.loc["Pack", "kg"] == pytest.approx(514.7856220198815)
    assert pack_environment.loc["GHGs", "total"] == pytest.approx(710776.1096187962)


def test_recycled_manufacturing_snapshot_tables_default():
    inputs = manufacturing_general_inputs("recycled").set_index("item")
    material_inputs = manufacturing_cell_material_inputs("recycled").set_index("material")
    environment = manufacturing_cell_environment_summary("recycled").set_index("metric")
    cost_summary = manufacturing_cell_cost_summary("recycled").set_index("item")

    assert inputs.loc["throughput", "value"] == 0
    assert inputs.loc["geographic_location", "value"] == "China"
    assert material_inputs.loc["Active cathode material", "kg_per_kg_cell"] == pytest.approx(0.5115937375662132)
    assert material_inputs.loc["NMP", "kg_per_kg_cell"] == pytest.approx(0.1461696393046323)
    assert material_inputs.loc["Binder (anode)", "kg_per_kg_cell"] == pytest.approx(0.006851701842404641)
    assert environment.loc["Total Energy", "energy_inputs"] == pytest.approx(0.06787769531209299)
    assert cost_summary.loc["Total", "Pyro"] == pytest.approx(0)


def test_recycled_cathode_material_environment_and_costs_default():
    direct_environment = manufacturing_recycled_cathode_material_environment("Direct").set_index("metric")
    costs = manufacturing_recycled_cathode_material_costs().set_index(["process", "chemistry"])

    assert direct_environment.loc["GHGs", "NMC(622)"] == pytest.approx(7547.895697081495)
    assert costs.loc[("Virgin", "NMC(622)"), "cost_per_kg_cathode"] == pytest.approx(25)
    assert costs.loc[("Pyro", "NMC(622)"), "cost_per_kg_cathode"] == pytest.approx(0)
