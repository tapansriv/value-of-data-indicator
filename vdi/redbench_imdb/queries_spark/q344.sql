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
    n.gender IS NULL
  )
  AND (
    n.name_pcode_nf IN ('C6252', 'D1616', 'D326', 'E6212', 'G6243', 'H4263', 'K6235', 'L6452', 'M6532', 'R1631', 'S2632', 'T3252')
  )
  AND (
    ci.note IN ('(director of development)', '(nurse)', '(producer)', '(production accountant)', '(script supervisor)', '(writer)')
    OR ci.note IS NULL
  )
  AND (
    rt.role IN ('composer', 'director', 'editor', 'miscellaneous crew', 'producer', 'writer')
  )
  AND (
    it1.id IN ('26')
  )
