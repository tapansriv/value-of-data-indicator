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
    n.name_pcode_nf IN ('C6215', 'C6426', 'D1314', 'H626', 'K314', 'M452', 'M526', 'P2415', 'S1254')
  )
  AND (
    ci.note IN ('(executive producer)') OR ci.note IS NULL
  )
  AND (
    rt.role IN ('actor', 'composer', 'producer')
  )
  AND (
    it1.id IN ('31')
  )
