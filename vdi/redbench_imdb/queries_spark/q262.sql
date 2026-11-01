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
    n.name_pcode_nf IN ('A5242', 'B5263', 'C6431', 'D5213', 'E4523', 'E62', 'E6256', 'G516', 'G6564', 'J54', 'K4235', 'L2426', 'L2621', 'M2164', 'M3243', 'M4245', 'M625', 'M6425', 'P3653', 'P5252', 'R562', 'T535', 'V2363')
  )
  AND (
    ci.note IN ('(computer/video playback supervisor)', '(contributing writer)', '(executive producer)', '(location manager)', '(other crew)', '(producer)', '(production assistant)', '(production secretary)', '(researcher)')
    OR ci.note IS NULL
  )
  AND (
    rt.role IN ('cinematographer', 'composer', 'director', 'editor', 'miscellaneous crew', 'producer', 'production designer')
  )
  AND (
    it1.id IN ('26')
  )
