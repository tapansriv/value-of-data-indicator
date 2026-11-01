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
    n.gender IN ('f', 'm')
  )
  AND (
    n.name_pcode_nf IN ('B6535', 'C2', 'C625', 'I5235', 'J1316', 'J2545', 'J2616', 'K1512', 'L2132', 'L5451', 'N1645', 'P3243', 'S632', 'T6235')
  )
  AND (
    ci.note IN ('(as Naprey)', '(associate producer)', '(director of photography)', '(executive producer)', '(producer)', '(script revision)', '(uncredited)')
    OR ci.note IS NULL
  )
  AND (
    rt.role IN ('actor', 'actress', 'cinematographer', 'miscellaneous crew', 'producer', 'writer')
  )
  AND (
    it1.id IN ('34')
  )
