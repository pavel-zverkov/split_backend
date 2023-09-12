from ..logger import logger


def find_common_subsequences(nums1: list, nums2: list) -> list:
    n = len(nums1)
    m = len(nums2)

    i = 0
    common_seq = []
    while i < n - 1:
        base_list = nums1[i:i + 2]
        common_sub_seq = []
        j = 0

        while j < m - 1 and not common_sub_seq:
            logger.trace(f'Indexes - {[i, j]}')
            compare_list = nums2[j:j + 2]

            logger.debug(f'base_list - {base_list}')
            logger.debug(f'compare_list - {compare_list}')

            if base_list == compare_list:
                while True:
                    common_sub_seq = base_list
                    logger.debug(f'Common sub seq - {common_sub_seq}')

                    if i + 2 == n or j + 2 == m:
                        common_seq.append(common_sub_seq)
                        break

                    elif nums1[i + 2] == nums2[j + 2]:

                        common_sub_seq.append(nums1[i + 2])
                        i += 1
                        j += 1

                        continue

                    else:
                        common_seq.append(common_sub_seq)
                        break

            j += 1
        i += 1

    return common_seq


if __name__ == '__main__':
    r = [31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 54, 55, 41,
         42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 100]
    l = [32, 33, 44, 50, 45, 48, 46, 49, 31, 51, 34,
         41, 55, 37, 38, 39, 54, 36, 35, 52, 53, 100]
    logger.info(find_common_subsequences(l, r))
