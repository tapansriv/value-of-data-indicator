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
    n.name_pcode_nf IN ('A2425', 'A5354', 'D1361', 'E6212', 'G4526', 'J252', 'J565', 'S5162')
  )
  AND (
    ci.note IS NULL
  )
  AND (
    rt.role IN ('actor', 'actress')
  )
  AND (
    it1.id IN ('31')
  )
