from ontopy import ontology


mammos_ontology = ontology.get_ontology(
    "https://raw.githubusercontent.com/MaMMoS-project/MagneticMaterialsOntology/refs/heads/main/magnetic_material_mammos.ttl"
).load()
