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
    n.name_pcode_nf IN ('A4252', 'D1562', 'I5216', 'K2532', 'K3214', 'K3525', 'L4653', 'M525', 'M5426', 'M6261', 'N24', 'N3262', 'R2153')
  )
  AND (
    ci.note IN ('(uncredited)') OR ci.note IS NULL
  )
  AND (
    rt.role IN ('actress')
  )
  AND (
    it1.id IN ('22')
  )
