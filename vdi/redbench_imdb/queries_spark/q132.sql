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
    n.gender IN ('m') OR n.gender IS NULL
  )
  AND (
    n.name_pcode_nf IN ('B1324', 'B6162', 'B6342', 'D1321', 'F6323', 'G6561', 'H5265', 'J2541', 'K1565', 'N214', 'R1214', 'R5452', 'S2536', 'W465')
  )
  AND (
    ci.note IN ('(script supervisor)', '(series story editor)', '(uncredited)', '(video)', '(writer) (as Onay Sales)')
    OR ci.note IS NULL
  )
  AND (
    rt.role IN ('actor', 'composer', 'director', 'miscellaneous crew', 'writer')
  )
  AND (
    it1.id IN ('22')
  )
