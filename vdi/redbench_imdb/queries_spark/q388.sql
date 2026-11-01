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
    n.gender IN ('f', 'm') OR n.gender IS NULL
  )
  AND (
    n.name_pcode_nf IN ('C4626', 'D3626', 'J1352', 'J6265', 'K5352', 'O351', 'V6532')
  )
  AND (
    ci.note IN ('(uncredited)', '(writer)') OR ci.note IS NULL
  )
  AND (
    rt.role IN ('actor', 'actress', 'composer', 'writer')
  )
  AND (
    it1.id IN ('32')
  )
