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
    n.name_pcode_nf IN ('G2125', 'R2632', 'R3145', 'S2516', 'T3216', 'W4265')
  )
  AND (
    ci.note IN ('(archive footage)', '(as Susana Borges)') OR ci.note IS NULL
  )
  AND (
    rt.role IN ('actor', 'actress')
  )
  AND (
    it1.id IN ('32')
  )
