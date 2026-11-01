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
    n.name_pcode_nf IN ('A4253', 'A5362', 'A6532', 'C6231', 'C6235', 'M6216', 'R1634', 'R516', 'R5316', 'S3162', 'S3521')
  )
  AND (
    ci.note IN ('(deviser)', '(overall in charge of promotion)', '(producer)', '(senior producer)', '(supervising producer)')
    OR ci.note IS NULL
  )
  AND (
    rt.role IN ('cinematographer', 'composer', 'director', 'editor', 'miscellaneous crew', 'producer', 'production designer', 'writer')
  )
  AND (
    it1.id IN ('19')
  )
