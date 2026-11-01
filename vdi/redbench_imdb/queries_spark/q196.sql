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
    n.gender IN ('m')
  )
  AND (
    n.name_pcode_nf IN ('D5254', 'E6236', 'F6521', 'H6325', 'J2545', 'J5365', 'K5452', 'M265', 'N2452', 'P6362')
  )
  AND (
    ci.note IS NULL
  )
  AND (
    rt.role IN ('actor', 'director')
  )
  AND (
    it1.id IN ('26')
  )
