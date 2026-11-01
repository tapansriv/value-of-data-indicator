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
    n.gender IN ('f')
  )
  AND (
    n.name_pcode_nf IN ('A3425', 'B2562', 'B32', 'C3454', 'C4626', 'D526', 'D5656', 'E125', 'E1265', 'E4535', 'F4652', 'G64', 'M4525', 'M6362', 'M6452', 'N5316', 'R2416', 'S536', 'V4535', 'V5256', 'Y2365')
  )
  AND (
    ci.note IN ('(dialogue coach)', '(uncredited)') OR ci.note IS NULL
  )
  AND (
    rt.role IN ('actress', 'director', 'miscellaneous crew')
  )
  AND (
    it1.id IN ('19')
  )
