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
    n.name_pcode_nf IN ('C6231', 'E5412', 'G2312', 'J2535', 'K454', 'M6416', 'O4165', 'R2162', 'R52', 'S1532', 'S5653', 'W4523')
  )
  AND (
    ci.note IN ('(associate director)', '(executive producer) (as Kylie M. Balagtas)', '(executive producer: BBC)', '(first assistant accountant) (uncredited)', '(production assistant)', '(production coordinator)', '(supervising producer)', '(writer)')
    OR ci.note IS NULL
  )
  AND (
    rt.role IN ('director', 'editor', 'miscellaneous crew', 'producer', 'writer')
  )
  AND (
    it1.id IN ('25')
  )
