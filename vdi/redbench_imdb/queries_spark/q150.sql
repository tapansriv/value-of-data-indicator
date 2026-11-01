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
    n.name_pcode_nf IN ('A5164', 'A5323', 'D5234', 'D5452', 'E5252', 'G6253', 'J252', 'J56', 'L4525', 'T6236')
  )
  AND (
    ci.note IN ('(voice)') OR ci.note IS NULL
  )
  AND (
    rt.role IN ('actress')
  )
  AND (
    it1.id IN ('22')
  )
