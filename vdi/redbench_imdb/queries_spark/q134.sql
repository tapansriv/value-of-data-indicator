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
    n.name_pcode_nf IN ('A4562', 'B6324', 'C6216', 'G6232', 'J154', 'J2126', 'J525', 'J5626', 'M6261', 'M6265', 'N2423', 'S6215', 'T164', 'T32', 'T532')
  )
  AND (
    ci.note IN ('(associate producer)', '(director of photography)', '(idea)', '(location scout)', '(producer)', '(production assistant)', '(writing supervised by)')
    OR ci.note IS NULL
  )
  AND (
    rt.role IN ('cinematographer', 'composer', 'editor', 'miscellaneous crew', 'producer', 'writer')
  )
  AND (
    it1.id IN ('22')
  )
