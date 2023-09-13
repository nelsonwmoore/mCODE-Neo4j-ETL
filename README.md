# mCODE-Neo4j-ETL
Load mCODE data to a Neo4j Database

## Requirements:
- Neo4j:
  - Neo4j version `4.2.x`
  - [CyFHIR](https://github.com/Optum/CyFHIR#how-to-use-cyfhir)
  - [APOC](https://github.com/neo4j-contrib/neo4j-apoc-procedures/releases)
- Python:
  - Python version `3.11`
  - `pip install click`
  - `pip install neo4j`

## Example Cypher Queries
These queries use the synthetic patient records in `/sample_mcode_data/` [generated by MITRE with Synthea](https://confluence.hl7.org/pages/viewpage.action?pageId=80119851#mCODETestData-SyntheaSyntheticDataforTestingmCODE-basedapplications)

### (1) What external coding systems are used and how many different codes are found in each system?
>`MATCH (n) WHERE n.code IS NOT NULL AND n.system IS NOT NULL AND NOT n.system CONTAINS "hl7.org"`\
>`RETURN n.system as system, COUNT(DISTINCT n.code) AS codes ORDER BY codes DESC`

### Returns:
| system | codes |
| - | - |
| http://snomed.info/sct | 308 |
| http://loinc.org | 204 |
| http://www.nlm.nih.gov/research/umls/rxnorm | 39 |
| http://unitsofmeasure.org | 27 |
| http://cancerstaging.org | 5 |
| urn:oid:2.16.840.1.113883.6.238 | 4 |
| http://dicom.nema.org/medical/dicom/current/output/chtml/part16/sect_CID_29.html | 3 |
| urn:ietf:rfc:3986 | 3 |
| urn:ietf:bcp:47 | 1 |
| http://ihe.net/fhir/ValueSet/IHE.FormatCode.codesystem | 1 |


### (2) For a given patient, what imaging procedures have been performed and on which anatomic sites?
>`MATCH (:name {family: "Cummings51", given: "[Errol226]", use: "official"})<-[:name]-(b:resource {resourceType: "Patient"}),`\
>`(b)<-[:resource]-(c:entry)<-[:reference]-(:subject)<-[:subject]-(e:resource {resourceType: "ImagingStudy"})-[:series]->(:series)-[:bodySite]->(g:bodySite),`
>`(e)-[:procedureCode]->(:procedureCode)-[:coding]->(i:coding)`
>`RETURN DISTINCT g.display as body_site, g.code as site_code, i.display as procedure, i.code as procedure_code, i.system as system`

### Returns:
| body_site | site_code | procedure | procedure_code | system |
| - | - | - | - | - |
| Thoracic structure (body structure)  | 51185008  | High resolution computed tomography of chest without contrast (procedure) | 16335031000119103  | http://snomed.info/sct |
| Heart structure (body structure)     | 80891009  | Echocardiography (procedure)                    | 40701008           | http://snomed.info/sct |
| Thoracic structure (body structure)  | 51185008  | Plain chest X-ray (procedure)                   | 399208008          | http://snomed.info/sct |

### (3) For a given patient, what were the 5 most recent observations, their codes, and values?
>`MATCH (a:name {family: "Breitenberg711", given: "[Aimee901]", use: "official"})<-[:name]-(b:resource {resourceType: "Patient"}),`
>`(b)<-[:resource]-(:entry)<-[:reference]-(:subject)<-[:subject]-(c:resource {resourceType: "Observation"})-[:code]->(:code)-[:coding]->(e:coding),`
>`(c)-[:valueQuantity]->(d:valueQuantity)`
>`RETURN d.value as value, d.unit as unit, e.display as display, e.code as code, e.system as system ORDER BY c.effectiveDateTime DESC LIMIT 5`

### Returns:
| value | unit | display | code | system |
| - | - | - | - | - |
| 1 | {score} | Total score [AUDIT-C] | 75626-2 | http://loinc.org |
| 24 | {score} | Patient Health Questionnaire 9 item (PHQ-9) total score [Reported] | 44261-6 | http://loinc.org |
| 4 | {score} | Patient Health Questionnaire 2 item (PHQ-2) total score [Reported] | 55758-7 | http://loinc.org |
| 0 | {score} | Total score [HARK] | 76504-0 | http://loinc.org |
| 69.1 | kg | Body Weight | 29463-7 | http://loinc.org |
