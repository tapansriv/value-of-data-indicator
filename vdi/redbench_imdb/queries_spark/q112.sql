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
    n.name_pcode_nf IN ('A4163', 'B3126', 'B3245', 'B5264', 'D1354', 'E6212', 'J242', 'K5616', 'M2426', 'M6241', 'P1423', 'P3654', 'R2542', 'S1524', 'W4513', 'W4515')
  )
  AND (
    ci.note IN ('(comic strip Mutt and Jeff)', '(executive producer)', '(producer)')
    OR ci.note IS NULL
  )
  AND (
    rt.role IN ('actor', 'actress', 'composer', 'director', 'producer', 'writer')
  )
  AND (
    it1.id IN ('37')
  )
