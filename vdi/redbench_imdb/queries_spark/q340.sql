SELECT
  COUNT(*)
FROM name AS n, aka_name AS an, info_type AS it1, person_info AS pi1, cast_info AS ci, role_type AS rt
WHERE
  n.id = ci.person_id
  AND ci.person_id = pi1.person_id
  AND it1.id = pi1.info_type_id
  AND n.id = pi1.person_id
  AND n.id = an.person_id
  AND ci.person_id = an.person_id
  AND an.person_id = pi1.person_id
  AND rt.id = ci.role_id
  AND (
    n.gender IN ('f') OR n.gender IS NULL
  )
  AND (
    n.name_pcode_nf IN ('A5253', 'A5312', 'A5352', 'B23', 'B2453', 'B4245', 'B5252', 'C3252', 'C4326', 'D4254', 'E3526', 'H4651', 'J523', 'L2324', 'L2362', 'L2645', 'M261', 'M3232', 'P2136', 'P2316', 'R2426', 'R256', 'S2536', 'S4121', 'V6521')
  )
  AND (
    ci.note IN ('(as Rebecca Cartwright)', '(assistant script editor)', '(creator)', '(director of photography)', '(executive producer)', '(production assistant)', '(script supervisor)', '(uncredited)', '(voice)', '(writer)', '(written by)')
    OR ci.note IS NULL
  )
  AND (
    rt.role IN ('actress', 'cinematographer', 'composer', 'director', 'miscellaneous crew', 'producer', 'writer')
  )
  AND (
    it1.id IN ('31')
  )
