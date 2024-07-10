# LAU geometries extraction

To meet the demand for statistics at a local level, Eurostat maintains a system of Local Administrative Units (LAUs) compatible with the Nomenclature of territorial units for statistics (NUTS). The upper LAU level (LAU level 1, formerly NUTS level 4) was defined for most, but not all of the countries. The lower LAU level (LAU level 2, formerly NUTS level 5) consisted of municipalities or equivalent units in the 28 European Union Member States. 

The plain text of the input MS Excel rows (events) contains two relevant columns with the pieces of information about LAUs. The first column is 'Reference mountain landscape' (RML) which often contains a string that coincides with the name of the LAU. The second column is 'LAU' which often contains the code of the LAU level 2. Unfortunately, the source data are not so accurate and complete and therefore there are exceptions to this rule. The first step is the create some regular expressions to extract the most relevant pieces of information and clean data from disturbing fragments, e.g. the fragment "LAU" before the code in the LAU column. Eventually, the Value Chain ID is necessary to extract the country code because it contains the ISO 3166-1 alpha-2 code, which serves to validate the extracted information since the same LAU code or name can be used for different LAUs in different countries.

The geospatial data of the LAUs have been extracted from the GeoJSON file provided by the Geographic Information System of the COmmission (GISCO). GISCO provides LAUs every year (since 2011) in multiple formats such as SHP, TopoJSON, GeoJSON, GDB and SVG. We decided to use the GeoJSON LAUs 2020. This file has CNTR_CODE, LAU_ID, LAU_NAME fields which contain respectively the two letters country code, the LAU code and the name of the LAU. 


``` 
For each event in the input Excel file:
    Extract the country code from the Value Chain ID
    Clean and extract relevant information from 'Reference mountain landscape' and 'LAU' columns
    Check if the LAU code exists in the GeoJSON LAUs 2020 file:
        If yes:
            Find the matching LAU by LAU_ID
            Check if the country code of the match is the same as the event's country code:
                If yes:
                    Extract the polygon of the LAU
                    Compute the weighted centroid of the polygon
                    Go to next event
        If no:
            Search for the 'Reference mountain landscape' string through the Wikidata SPARQL endpoint
            If a match is found:
                Extract the NUTS3 code from the match
                Check if the NUTS3 code exists in the GeoJSON NUTS codes file:
                    If yes:
                        Find the matching NUTS3 by NUTS_ID
                        Find the matching LAU by NUTS_ID
                        Check if the country code of the match is the same as the event's country code:
                            If yes:
                                Extract the polygon of the LAU
                                Compute the weighted centroid of the polygon
                                Go to next event
            Otherwise:
                Go to next event

```

The algorithm works this way, for every event clean the two fields with a set of regular expressions and extract the country code from the Value Chain identifier.
Firstly search if exist the value of 'RML' in the GeoJSON LAUs 2020 file, searching by LAU_NAME. Then search if exist the 'LAU' in the GeoJSON LAUs 2020 file, searching by LAU_ID. If the algorithm finds a match, it checks if the country code of the match is the same as the country code of the event. If the answer is positive the LAU is found and the algorithm extracts the polygon of the LAU, computes the centroid, which is weighted by the area of each polygon, and goes to the next event. Otherwise, it searches the string that represents the Reference mountain landscape through the Wikidata SPARQL endpoint. Sometimes in the LAU field, it is possible to find the NUTS3 code. In these cases, the algorithm searches the code in the GeoJSON of NUTS codes, provided by GISCO. 


