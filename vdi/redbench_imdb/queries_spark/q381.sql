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
    n.name_pcode_nf IN ('A542', 'B3143', 'B3626', 'B5325', 'B6215', 'B6234', 'C2164', 'J5432', 'L1235', 'M2156', 'M636', 'N1236', 'N45', 'R5252', 'S3562', 'S5324', 'Z2513')
  )
  AND (
    ci.note IN ('(producer)', '(production assistant)', '(switcher)', '(uncredited)', '(voice: English version)', '(writer)')
    OR ci.note IS NULL
  )
  AND (
    rt.role IN ('actor', 'actress', 'composer', 'editor', 'miscellaneous crew', 'producer', 'writer')
  )
  AND (
    it1.id IN ('31')
  )
