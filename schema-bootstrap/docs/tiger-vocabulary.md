# TIGER/Line place vocabularies, as they appear in `tl_2023_49_place`

Utah incorporated places and CDPs, U.S. Census Bureau TIGER/Line 2023. 334 rows.
Source: [`tl_2023_49_place.zip`](https://www2.census.gov/geo/tiger/TIGER2023/PLACE/tl_2023_49_place.zip).

The DISTINCT pass finds a column's value vocabulary in about a second. It cannot find what
the values mean. This file is the other half: every code present in the extract, with its
meaning sourced from the Census Bureau, and the ones the authority does not cover called out
rather than guessed.

Two limits worth carrying into any model built from this. First, these are the values
PRESENT IN THIS EXTRACT, not the values legal in the domain -- STATEFP below has exactly one
value here and fifty-six in the United States. Second, an absent code is not an invalid
code: LSAD 35 is real, is used five times, and is not on the Census code list.

## `LSAD`

Authority: <https://www.census.gov/library/reference/code-lists/legal-status-codes.html>

| code | rows | meaning |
|---|---:|---|
| `25` | 147 | city (suffix) |
| `35` | 5 | **not in the authority** -- see note below |
| `43` | 103 | town (suffix) |
| `57` | 79 | CDP (suffix) |

## `CLASSFP`

Authority: <https://www.census.gov/library/reference/code-lists/class-codes.html>

| code | rows | meaning |
|---|---:|---|
| `C1` | 255 | An active incorporated place that does not serve as a county subdivision equivalent |
| `M2` | 1 | A military or other defense installation entirely within a place |
| `U1` | 73 | A census designated place with an official federally recognized name |
| `U2` | 5 | A census designated place without an official federally recognized name |

## `FUNCSTAT`

Authority: <https://www.census.gov/library/reference/code-lists/functional-status-codes.html>

| code | rows | meaning |
|---|---:|---|
| `A` | 255 | Active government providing primary general-purpose functions |
| `S` | 79 | Statistical entity |

## `MTFCC`

Authority: <https://www2.census.gov/geo/pdfs/reference/mtfccs2022.pdf>

| code | rows | meaning |
|---|---:|---|
| `G4110` | 255 | Incorporated Place — A legal entity incorporated under state law to provide general-purpose governmental services to a concentration of population.... |
| `G4210` | 79 | Census Designated Place — A statistical area that is defined for a named concentration of population and is the statistical counterpart of an incor... |

## `PCICBSA`

No Census code list located for this field.

| code | rows | meaning |
|---|---:|---|
| `N` | 321 | **not in the authority** -- see note below |
| `Y` | 13 | **not in the authority** -- see note below |

## `LSAD` 35 -- the code the authority does not have

Five rows carry LSAD 35 and the Census legal-status code list has no entry for it. The data
answers the question the authority could not: NAMELSAD for those rows reads "Copperton metro
township", "Emigration Canyon metro township", and so on. So LSAD 35 is 'metro township
(suffix)' -- a Utah-specific municipal form created in 2015, present in the extract and
missing from the national code list.

This is the case worth showing in a room. The mechanical pass found the value, the authority
failed to explain it, and a sibling column settled it. A model that promoted the DISTINCT
output straight to a closed enum would have carried an undocumented member and nobody would
have noticed.

## `STATEFP` -- one value here, fifty-six in the domain

STATEFP came back with a single distinct value, 49, because this extract is Utah. A DISTINCT
pass over one file reports 49 as the whole vocabulary. It is a FIPS state code with fifty-
six legal values. Anything inferred from one extract is a lower bound on its domain, which
is why the generated enums carry that warning in their docstrings.

