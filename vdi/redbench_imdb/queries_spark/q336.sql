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
    n.name_pcode_nf IN ('B1236', 'C2362', 'C565', 'G5636', 'I4216', 'K1352', 'K4165', 'L2162', 'O2541', 'R2526', 'R523', 'S3151', 'S5635', 'T5252')
  )
  AND (
    ci.note IN ('(archive footage)', '(executive producer)', '(producer)', '(stand-in) (uncredited)', '(voice)')
    OR ci.note IS NULL
  )
  AND (
    rt.role IN ('actor', 'actress', 'cinematographer', 'director', 'miscellaneous crew', 'producer')
  )
  AND (
    it1.id IN ('31')
  )
