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
    n.gender IN ('f') OR n.gender IS NULL
  )
  AND (
    n.name_pcode_nf IN ('A1245', 'A6514', 'D5416', 'E5252', 'F6525', 'G4314', 'J4526', 'J5162', 'K1525', 'K5452', 'L2424', 'L6536', 'M6263', 'N6165', 'R1634', 'S312', 'Y26')
  )
  AND (
    ci.note IN ('(director of photography)', '(executive in charge of promotions) (as Robert G. Labayen)', '(story editor)', '(supervising producer)', '(voice)')
    OR ci.note IS NULL
  )
  AND (
    rt.role IN ('actress', 'cinematographer', 'director', 'editor', 'miscellaneous crew', 'producer')
  )
  AND (
    it1.id IN ('19')
  )
