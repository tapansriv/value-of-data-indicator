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
    n.gender IN ('m')
  )
  AND (
    n.name_pcode_nf IN ('A2324', 'A5361', 'B4652', 'C6243', 'D2426', 'E1623', 'F2162', 'G6512', 'J5262', 'K6242', 'L21', 'L2656', 'L6212', 'N5251', 'P3624', 'P4252', 'P5352', 'R521', 'R5325', 'R5354', 'S1232', 'T1524', 'V2361', 'Y2562', 'Z5352')
  )
  AND (
    ci.note IN ('(creator)', '(executive producer)', '(producer)', '(stand-in) (uncredited)')
    OR ci.note IS NULL
  )
  AND (
    rt.role IN ('actor', 'cinematographer', 'composer', 'director', 'miscellaneous crew', 'producer', 'writer')
  )
  AND (
    it1.id IN ('19')
  )
